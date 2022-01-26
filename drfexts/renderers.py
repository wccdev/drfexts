import datetime
from typing import Mapping, Optional, Union, Any

import ujson
import unicodecsv as csv
from io import BytesIO

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.status import is_success


class CustomJSONRenderer(JSONRenderer):
    """
    Renderer which serializes to JSON.
    Applies JSON's backslash-u character escaping for non-ascii characters.
    Uses the blazing-fast ujson library for serialization.
    """

    # Controls whether forward slashes (/) are escaped.
    escape_forward_slashes: bool = False
    # Used to enable special encoding of "unsafe" HTML characters into safer
    # Unicode sequences.
    encode_html_chars: bool = False

    def render(
        self,
        data: Union[dict, None],
        accepted_media_type: Optional[str] = None,
        renderer_context: Mapping[str, Any] = None,
    ) -> bytes:

        accepted_media_type = accepted_media_type or ""
        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context)
        response = renderer_context['response']
        status_code = getattr(response, 'error_code', response.status_code)
        response.status_code = status.HTTP_200_OK
        playload = {
            "ret": status_code,
            "msg": "success",
        }

        if data is not None:
            playload["data"] = data

        if not is_success(status_code):
            try:
                playload["msg"] = data["detail"]
                playload.pop("data", None)
            except Exception:
                playload["msg"] = "error"
        else:
            playload["ret"] = status.HTTP_200_OK

        ret = ujson.dumps(
            playload,
            ensure_ascii=self.ensure_ascii,
            escape_forward_slashes=self.escape_forward_slashes,
            encode_html_chars=self.encode_html_chars,
            indent=indent or 0,
        )

        # force return value to unicode
        if isinstance(ret, str):
            # We always fully escape \u2028 and \u2029 to ensure we output JSON
            # that is a strict javascript subset. If bytes were returned
            # by json.dumps() then we don't have these characters in any case.
            # See: http://timelessrepo.com/json-isnt-a-javascript-subset
            ret = ret.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
            return bytes(ret.encode("utf-8"))
        return ret


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
        """ Convert given row and column number to an Excel-style cell name. """
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
