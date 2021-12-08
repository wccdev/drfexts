import datetime

import openpyxl
import unicodecsv as csv
from io import BytesIO

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from rest_framework import status
from rest_framework.renderers import JSONRenderer, BaseRenderer
from rest_framework.status import is_success
from rest_framework.response import Response
from rest_framework_csv.renderers import CSVRenderer


class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context['response']
        status_code = getattr(response, 'error_code', response.status_code)
        response.status_code = status.HTTP_200_OK
        playload = {
            "ret": status_code,
            "msg": "success",
            "data": data,
        }

        if not is_success(status_code):
            playload["data"] = None
            try:
                playload["msg"] = data["detail"]
            except Exception:
                playload["msg"] = "failed"
                playload["data"] = data
        else:
            playload["ret"] = status.HTTP_200_OK

        return super(CustomJSONRenderer, self).render(playload, accepted_media_type, renderer_context)


class BaseExportRenderer(BaseRenderer):
    def validate(self, data):
        return True

    def get_export_data(self, data):
        return data["results"] if "results" in data else data

    def get_file_name(self, renderer_context):
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

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders serialized *data* into CSV. For a dictionary:
        """
        renderer_context = renderer_context or {}
        if data is None:
            return ''

        if not isinstance(data, list):
            data = [data]

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

        data = data["data"]["list"]

        header = renderer_context.get('header', self.header)
        labels = renderer_context.get('labels', self.labels)
        value_mapping = renderer_context.get('value_mapping')

        table = self.tablize(data, header=header, labels=labels, value_mapping=value_mapping)
        excel_buffer = BytesIO()

        workbook = Workbook()
        sheet = workbook.active

        for row in table:
            sheet.append(row)

        font = Font(b=True)
        fill = PatternFill(bgColor="FFC7CE", fill_type="solid")

        for cell in sheet["1:1"]:
            cell.font = font
            cell.fill = PatternFill('solid', start_color="87CEFA")
            cell.alignment = Alignment(vertical='center')

        sheet.row_dimensions[1].height = 17
        sheet.freeze_panes = f"A2"

        sheet.print_title_rows = '1:1'
        workbook.save(excel_buffer)

        filename = self.get_file_name(renderer_context)
        renderer_context["response"]['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return excel_buffer.getvalue()
