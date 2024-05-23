from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import numpy as np

class AzureDocProcessor:
    def __init__(self, endpoint, key) -> None:
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

    def read_pg_data(self, doc_path):
        with open(doc_path, "rb") as f:
               poller = self.document_analysis_client.begin_analyze_document(
                   "prebuilt-document", document=f, locale="en-US"
               )
        self.result = poller.result()

    def format_polygon(self, polygon):
        if not polygon:
            return "N/A"
        return "["+", ".join(["[{}, {}]".format(p.x, p.y) for p in polygon])+"]"
    
    def add_to_dict_of_lists(self, target_dict, key, item_to_add_to_list): 
        if target_dict.get(key) is None:
            target_dict[key] = [item_to_add_to_list]
        else:
            target_dict[key].append(item_to_add_to_list)

    def bbox1_contains_bbox2(self, bbox1, bbox2): 
        topleft_1 = bbox1[0]
        topleft_2 = bbox2[0]
        botright_1 = bbox1[2]
        botright_2 = bbox2[2]
        if topleft_1[0] <= topleft_2[0] + 0.1 and topleft_1[1] <= topleft_2[1] + 0.1:
            if botright_1[0] >= botright_2[0] - 0.1 and botright_1[1] >= botright_2[1] - 0.1:
                return True
        return False
    
    def ignore_para(self, para_pgno, para_bbox, bboxes_to_ignore):
        if para_pgno not in bboxes_to_ignore.keys():
            return False
        para_bbox = eval(para_bbox)
        for bbox in bboxes_to_ignore[para_pgno]:
            bbox = eval(bbox)
            if self.bbox1_contains_bbox2(bbox, para_bbox):
                return True
        return False

    def extract_text_n_tables(self, doc_path):
        self.read_pg_data(doc_path)
        tables = {}
        contents = {}
        bboxes_to_ignore = {}

        for table_idx, table in enumerate(self.result.tables):
            region = table.bounding_regions[0]
            if bboxes_to_ignore.get(region.page_number) is None:
                bboxes_to_ignore[region.page_number] = [self.format_polygon(region.polygon)]
            else:
                bboxes_to_ignore[region.page_number].append(self.format_polygon(region.polygon))
            np_table = np.empty((table.row_count, table.column_count)).tolist()
            for i in range(len(np_table)):
                for j in range(len(np_table[0])):
                    np_table[i][j] = ''
            for cell in table.cells:
                np_table[cell.row_index][cell.column_index] = cell.content
            self.add_to_dict_of_lists(tables, region.page_number, np_table)
        
        for para in self.result.paragraphs:
            region = para.bounding_regions[0]
            bbox = self.format_polygon(region.polygon)
            pgno = region.page_number
            if not self.ignore_para(pgno, bbox, bboxes_to_ignore):
                self.add_to_dict_of_lists(contents, pgno, para.content)
        
        return {
            'contents':contents,
            'tables':tables,
        }
    
    def prepare_to_chunks(self, extracted_data):
        chunked_slidewise = {}
        for page in extracted_data['contents'].keys():
            chunk_text = f'<<beginning of OCR output>>\n\nSlide #{page} text:\n' + '\n'.join([para for para in extracted_data['contents'][page]])
            if extracted_data.get('tables', None) is not None:
                if extracted_data['tables'].get(page, None) is not None:
                    chunk_text += f'\n\nSlide #{page} tables:\n---\n' + '\n---\n'.join(
                        ['\t|\n'.join(
                            ['|' + '\t|'.join(
                                [cell for cell in row]
                            ) for row in table]
                        ) + '\t|\n' for table in extracted_data['tables'][page]]
                    ) + '\n---\n'
            chunk_text += '\n\n<<end of OCR output>>'
            chunked_slidewise[page] = chunk_text
        return chunked_slidewise



def step_0(endpoint, key, doc_path):
    extractor = AzureDocProcessor(endpoint, key)
    extracted_data = extractor.extract_text_n_tables(doc_path)
    doc_processed = extractor.prepare_to_chunks(extracted_data)
    return [doc_processed[i] for i in doc_processed]
