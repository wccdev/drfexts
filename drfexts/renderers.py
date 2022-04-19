import functools
import operator
from decimal import Decimal

import orjson
from typing import Optional, Any
import unicodecsv as csv
from io import BytesIO
import datetime

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from rest_framework import status
from django.utils.encoding import force_str

from rest_framework.settings import api_settings
from rest_framework.renderers import BaseRenderer
from rest_framework.status import is_success
from django.utils.functional import Promise
from django.db.models.query import QuerySet

__all__ = ["CustomJSONRenderer", "CustomCSVRenderer", "CustomExcelRenderer"]


class CustomJSONRenderer(BaseRenderer):
    """
    Renderer which serializes to JSON.
    Uses the Rust-backed orjson library for serialization speed.
    """

    media_type = "application/json"
    html_media_type = "text/html"
    format = "json"
    charset = None

    options = functools.reduce(
        operator.or_,
        api_settings.user_settings.get("ORJSON_RENDERER_OPTIONS", ()),
        orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_PASSTHROUGH_DATETIME,
    )

    @staticmethod
    def default(obj: Any) -> Any:
        """
        When orjson doesn't recognize an object type for serialization it passes
        that object to this function which then converts the object to its
        native Python equivalent.

        :param obj: Object of any type to be converted.
        :return: native python object
        """

        if isinstance(obj, Promise):
            return force_str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime(api_settings.DATETIME_FORMAT)
        elif isinstance(obj, Decimal):
            if api_settings.COERCE_DECIMAL_TO_STRING:
                return str(obj)
            else:
                return float(obj)
        elif isinstance(obj, QuerySet):
            return tuple(obj)
        elif hasattr(obj, "tolist"):
            return obj.tolist()
        elif hasattr(obj, "__iter__"):
            return list(item for item in obj)

    def render(
        self,
        data: Any,
        media_type: Optional[str] = None,
        renderer_context: Any = None,
    ) -> bytes:
        """
        Serializes Python objects to JSON.

        :param data: The response data, as set by the Response() instantiation.
        :param media_type: If provided, this is the accepted media type, of the
                `Accept` HTTP header.
        :param renderer_context: If provided, this is a dictionary of contextual
                information provided by the view. By default this will include
                the following keys: view, request, response, args, kwargs
        :return: bytes() representation of the data encoded to UTF-8
        """
        if response := renderer_context.get('response'):
            playload = {
                "ret": response.status_code,
                "msg": "success",
            }

            if data is not None:
                playload["data"] = data

            if not is_success(response.status_code):
                try:
                    playload["msg"] = data["detail"]
                    playload.pop("data", None)
                except KeyError:
                    playload["msg"] = "error"

            response.status_code = status.HTTP_200_OK  # Set all response status to HTTP 200
        elif data is None:
            return b""
        else:
            playload = data

        # If `indent` is provided in the context, then pretty print the result.
        # E.g. If we're being called by RestFramework's BrowsableAPIRenderer.
        options = self.options
        if media_type == self.html_media_type:
            options |= orjson.OPT_INDENT_2

        response._rendered_data = playload  # for loging response use
        serialized: bytes = orjson.dumps(playload, default=self.default, option=options)
        return serialized


class BaseExportRenderer(BaseRenderer):
    def validate(self, data: dict):
        return True

    def get_export_data(self, data: dict):
        return data["results"] if "results" in data else data

    def get_file_name(self, renderer_context: Optional[dict]):
        return f'export({datetime.datetime.now().strftime("%Y%m%d")})'

    def tablize(self, data, header=None, labels=None, value_mapping=None):
        """
        Convert a list of data into a table.

        If there is a header provided to tablize it will efficiently yield each
        row as needed. If no header is provided, tablize will need to process
        each row in the data in order to construct a complete header. Thus, if
        you have a lot of data and want to stream it, you should probably
        provide a header to the renderer (using the `header` attribute, or via
        the `renderer_context`).
        """
        # Try to pull the header off of the data, if it's not passed in as an
        # argument.
        if not header and hasattr(data, 'header'):
            header = data.header

        if data:
            # First, flatten the data (i.e., convert it to a list of
            # dictionaries that are each exactly one level deep).  The key for
            # each item designates the name of the column that the item will
            # fall into.
            data = self.flatten_data(data)
            # Get the set of all unique headers, and sort them (unless already provided).
            if not header:
                # We don't have to materialize the data generator unless we
                # have to build a header.
                data = tuple(data)
                header_fields = set()
                for item in data:
                    header_fields.update(list(item.keys()))
                header = sorted(header_fields)

            # Return your "table", with the headers as the first row.
            if labels:
                yield [labels.get(x, x) for x in header]
            else:
                yield header
            # Create a row for each dictionary, filling in columns for which the
            # item has no data with None values.
            for item in data:
                if value_mapping:
                    row = [
                        value_mapping[key].get(item.get(key), item.get(key)) if key in value_mapping else item.get(key)
                        for key in header
                    ]
                else:
                    row = [item.get(key) for key in header]
                yield row
        elif header:
            # If there's no data but a header was supplied, yield the header.
            if labels:
                yield [labels.get(x, x) for x in header]
            else:
                yield header
        else:
            # Generator will yield nothing if there's no data and no header
            pass

    def flatten_data(self, data, value_mapping=None):
        """
        Convert the given data collection to a list of dictionaries that are
        each exactly one level deep. The key for each value in the dictionaries
        designates the name of the column that the value will fall into.
        """
        for item in data:
            yield dict(item)


class CustomCSVRenderer(BaseExportRenderer):
    """
    Renderer which serializes to CSV
    """

    media_type = 'text/csv'
    format = 'csv'
    header = None
    labels = None  # {'<field>':'<label>'}
    writer_opts = None
    data_key = "results"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders serialized *data* into CSV. For a dictionary:
        """
        renderer_context = renderer_context or {}
        if data is None:
            return bytes()

        if isinstance(data, dict):
            data = data[self.data_key]

        writer_opts = renderer_context.get('writer_opts', self.writer_opts or {})
        header = renderer_context.get('header', self.header)
        labels = renderer_context.get('labels', self.labels)
        value_mapping = renderer_context.get('value_mapping')
        encoding = renderer_context.get('encoding', settings.DEFAULT_CHARSET)

        table = self.tablize(data, header=header, labels=labels, value_mapping=value_mapping)
        csv_buffer = BytesIO()
        csv_writer = csv.writer(csv_buffer, encoding=encoding, **writer_opts)
        for row in table:
            csv_writer.writerow(row)

        filename = self.get_file_name(renderer_context)
        renderer_context["response"]['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return csv_buffer.getvalue()


class CustomExcelRenderer(BaseExportRenderer):
    """
    Renderer for Excel spreadsheet open data format (xlsx).
    """

    media_type = "application/xlsx"
    format = "xlsx"
    header = None
    labels = None  # {'<field>':'<label>'}
    boolean_labels = None
    custom_mappings = None
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    data_key = "results"
    header_font = Font(b=True)
    header_fill = PatternFill('solid', start_color="87CEFA")
    header_height = 17
    freeze_header = True

    def excel_style(self, row, col):
        """Convert given row and column number to an Excel-style cell name."""
        result = []
        while col:
            col, rem = divmod(col - 1, 26)
            result[:0] = self.letters[rem]
        return ''.join(result) + str(row)

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into XLSX workbook, returning a workbook.
        """
        if not self.validate(data):
            return bytes()

        if isinstance(data, dict):
            data = data[self.data_key]

        header = renderer_context.get('header', self.header)
        labels = renderer_context.get('labels', self.labels)
        value_mapping = renderer_context.get('value_mapping')

        table = self.tablize(data, header=header, labels=labels, value_mapping=value_mapping)
        excel_buffer = BytesIO()

        workbook = Workbook()
        sheet = workbook.active

        for row in table:
            sheet.append(row)

        for cell in sheet["1:1"]:
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(vertical='center')

        sheet.row_dimensions[1].height = self.header_height
        if self.freeze_header:
            sheet.freeze_panes = f"A2"

        sheet.print_title_rows = '1:1'
        workbook.save(excel_buffer)

        filename = self.get_file_name(renderer_context)
        renderer_context["response"]['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return excel_buffer.getvalue()
