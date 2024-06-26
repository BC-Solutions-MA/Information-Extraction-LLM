
from io import BufferedReader, FileIO
import os
from supabase import create_client, Client
import mimetypes

URL: str = "https://hxshejoduhitvgdqhxto.supabase.co"
SERVICE_KEY :str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4c2hlam9kdWhpdHZnZHFoeHRvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxNTc3NjkxOCwiZXhwIjoyMDMxMzUyOTE4fQ.nan7NUHTngr_0cazDms5dy3mGFOF2hIjtEkxDOIIolA"

STATUS = ["Used","Unused"]

class SupabaseAdapter :
    """
    A class that provides methods to interact with the Supabase database.

    Attributes:
        client (Client): The Supabase client used for database operations.

    Methods:
        __init__(self): Initializes the SupabaseAdapter class and creates a Supabase client.
        create_pipeline(self, name: str, config: dict, prompt: str) -> dict: Creates a new pipeline in the database.
        get_all_pipelines(self) -> list[dict]: Retrieves all pipelines from the database.
        get_pipeline_by_id(self, id: str) -> dict: Retrieves a pipeline by its ID from the database.
        search_pipeline_by_name(self, name: str) -> list[dict]: Searches for pipelines by name in the database.
        _upload_file(self, file: BufferedReader | bytes | FileIO, file_name: str) -> dict: Uploads a file to the Supabase storage.
        new_file(self, file: BufferedReader | bytes | FileIO, file_name: str, pipeline_id: str) -> str: Creates a new file entry in the database and uploads the file to the storage.
        update_file_ocr_result(self, file_id: str, ocr_json: dict, ocr_text: str) -> dict: Updates the OCR result of a file in the database.
        update_file_llm_result(self, file_id: str, llm_json: dict, llm_score: float) -> dict: Updates the LLM result of a file in the database.
        update_file_validation_result(self, file_id: str, corrected: dict, corrected_score: float) -> dict: Updates the validation result of a file in the database.
    """
    client: Client = None
    
    def __init__(self):
        self.client = create_client(URL, SERVICE_KEY)
        
    def create_pipeline(self, name: str, config: dict, prompt: str) -> dict:
        """
        Creates a pipeline with the given name, configuration, and prompt.

        Args:
            name (str): The name of the pipeline.
            config (dict): The configuration for the pipeline.
            prompt (str): The prompt for the pipeline.

        Returns:
            dict: The data of the created pipeline.
        """
        return self.client.table("Pipelines").insert({"name": name, "config": config, "prompt": prompt}).execute().data[0]

    
    def get_all_pipelines(self) -> list[dict]:
        """
        Retrieves all pipelines from the 'Pipelines' table.
        
        Returns:
            A list of dictionaries representing the pipelines.
        """
        return self.client.table("Pipelines").select("*").execute().data
    
    def get_pipeline_by_id(self, id: str) -> dict:
        """
        Retrieves a pipeline from the 'Pipelines' table based on the provided ID.
        
        Args:
            id (str): The ID of the pipeline to retrieve.
            
        Returns:
            dict: A dictionary representing the retrieved pipeline.
        """
        return self.client.table("Pipelines").select("*").eq("id", id).execute().data[0]
        
    def search_pipeline_by_name(self, name: str) -> list[dict]:
        """
        Searches for pipelines by name.
        
        Args:
            name (str): The name to search for.
            
        Returns:
            list[dict]: A list of dictionaries representing the pipelines that match the search criteria.
        """
        return self.client.table("Pipelines").select("*").ilike("name", f"%{name}%").execute().data
    
    def delete_pipeline(self, id: str) -> dict:
        """
        Deletes a pipeline from the 'Pipelines' table.
        
        Args:
            id (str): The ID of the pipeline to delete.
            
        Returns:
            dict: The response from the database.
        """
        return self.client.table("Pipelines").delete().eq("id", id).execute().data[0]
    
    def _upload_file(self,file:BufferedReader ,file_name:str) -> dict:
        """
        Uploads a file to the storage.

        Args:
            file: The file to be uploaded. It can be a BufferedReader, bytes, or FileIO object.
            file_name: The name of the file.

        Returns:
            A dictionary containing the response from the storage API.

        """
        file_type = mimetypes.guess_type(file_name)[0]
        return self.client.storage.from_("kyc-files").upload(file_name,file,file_options={"content-type": file_type}).json()
    
    def new_file(self,file:BufferedReader,file_name:str) -> str:
        """
        Uploads a new file to the storage and inserts its metadata into the 'Files' table.
        
        Args:
            file (BufferedReader | bytes | FileIO): The file to be uploaded.
            file_name (str): The name of the file.
            pipeline_id (str): The ID of the pipeline.
            
        Returns:
            str: The ID of the inserted file.
            
        Raises:
            Any exceptions that may occur during the file upload or database insertion process.
        """
        uploaded_file = self._upload_file(file,file_name)
        file_insert = {
            "name":uploaded_file['Key'],
            "storage_id":uploaded_file["Id"],
            "status":STATUS[1]
        }
        return self.client.table("Files").insert(file_insert).execute().data[0]['id']
    
    def _delete_file_from_table(self,file_id:str) -> dict:
        """
        Deletes a file from the 'Files' table.

        Args:
            file_id (str): The ID of the file to delete.

        Returns:
            dict: The response from the database.
        """
        return self.client.table("Files").delete().eq("id",file_id).execute().data[0]
    
    def assign_file_to_pipeline(self,file_id:str,pipeline_id:str) -> str:
        """
        Assigns a file to a pipeline.

        Args:
            file_id (str): The ID of the file.
            pipeline_id (str): The ID of the pipeline.

        Returns:
            str: The id of the Results.
        """
        check = self.get_result(file_id,pipeline_id)
        if check is not None:
            return check["id"]
        self.client.table("Files").update({"status":STATUS[0]}).eq("id",file_id).execute()
        return self.client.table("Results").insert({"file_id":file_id,"pipeline_id":pipeline_id,"status":"pending OCR"}).execute().data[0]["id"]
    
    def get_result(self, file_id:str, pipeline_id:str) -> dict:
        """
        Retrieves the result of a file for a given pipeline.

        Args:
            file_id (str): The ID of the file.
            pipeline_id (str): The ID of the pipeline.

        Returns:
            dict: The result data. or None if no result is found.
        """
        resp = self.client.table("Results").select("*,Files(*)").eq("file_id",file_id).eq("pipeline_id",pipeline_id).execute().data
        if len(resp) > 0:
            return resp[0]
        return None
    
    def update_ocr_result(self,file_id:str,ocr_json:dict,ocr_text:str) -> dict:
        """
        Updates the OCR result of a file in the database.

        Args:
            result_id (str): The ID of the results row to update.
            ocr_json (dict): The OCR result in JSON format.
            ocr_text (str): The OCR result in plain text format.

        Returns:
            dict: The updated file record.
            
        Raises:
            Any exceptions that may occur during the database update process.
        """
        return self.client.table("Files").update({"ocr_json":ocr_json,"ocr_text":ocr_text,"status":"pending LLM"}).eq("id",file_id).execute().data[0]["id"]

    def create_llm_result(self,file_id: str, pipeline_id: str, llm_json:dict,) -> dict:
        """
        Updates the LLm result for a file in the database.

        Args:
            llm_json (dict): The LLm JSON data to update.
            llm_score (float): The LLm score to update.

        Returns:
            dict: The updated data for the file.
            
        Raises:
            Any exceptions that may occur during the database update process.
        """
        return self.client.table("Results").insert({"file_id": file_id, "pipeline_id": pipeline_id, "llm_json":llm_json, "status":"pending Val"}).execute().data[0]["id"]

    def update_validation_result(self,result_id:str,corrected:dict,corrected_score:float) -> dict:
        """
        Updates the validation result of a file in the database.

        Args:
            result_id (str): The ID of the file to update.
            corrected (dict): The corrected data for the file.
            corrected_score (float): The corrected score for the file.

        Returns:
            dict: The updated validation result of the file.
        
        Raises:
            Any exceptions that may occur during the database update process.
        """
        return self.client.table("Results").update({"corrected":corrected,"corrected_score":corrected_score,"status":"completed"}).eq("id",result_id).execute().data[0]["id"]
    
    def get_files_by_pipeline_id(self,pipeline_id:str) -> list[dict]:
        """
        Retrieves all files associated with a pipeline.

        Args:
            pipeline_id (str): The ID of the pipeline.

        Returns:
            list[dict]: A list of dictionaries representing the files associated with the pipeline.
        """
        return self.client.table("Results").select("*,Files(*)").eq("pipeline_id",pipeline_id).execute().data

    def get_file_by_id(self,file_id:str) -> dict:
        """
        Retrieves a file by its ID.

        Args:
            file_id (str): The ID of the file to retrieve.

        Returns:
            dict: A dictionary representing the retrieved file.
        """
        res = self.client.table("Files").select("*").eq("id",file_id).execute().data
        if len(res) > 0:
            return res[0]
        return None
    
    def get_file_url(self,file_id:str) -> str:
        """
        Retrieves the URL of the file from the storage.

        Args:
            file_id (str): The ID of the file.

        Returns:
            str: The URL of the file.
        """
        file = self.get_file_by_id(file_id)
        bucket = file["name"].split("/")[0]
        name = file["name"].split("/")[-1]
        return self.client.storage.from_(bucket).create_signed_url(name,3600)
    
    def get_all_files(self) -> list[dict]:
        """
        Retrieves all files from the 'Files' table.

        Returns:
            list[dict]: A list of dictionaries representing the files.
        """
        return self.client.table("Files").select("*").execute().data
    
    def delete_file(self,file_id:str) -> dict:
        """
        Retrieves the URL of the file from the storage.

        Args:
            file_id (str): The ID of the file.

        Returns:
            str: The URL of the file.
        """
        file = self._delete_file_from_table(file_id)
        bucket = file["name"].split("/")[0]
        name = file["name"].split("/")[-1]
        #self.client.table("Results").delete().eq("file_id",file_id).execute()
        return self.client.storage.from_(bucket).remove([name])[0]#.create_signed_url(name,3600)
# ----------------------------------------------------------
    
    def create_ocr_result(self, file_id: str, ocr_json: dict, ocr_text: str) -> dict:
        """
        Creates an ocr result with the given ocr_json, ocr_text, and file_id.

        Args:
            name (str): The name of the pipeline.
            config (dict): The configuration for the pipeline.
            prompt (str): The prompt for the pipeline.

        Returns:
            dict: The data of the created pipeline.
        """
        return self.client.table("Files").update({"ocr_json": ocr_json, "ocr_text": ocr_text}).eq("id", file_id).execute().data[0]

    def get_all_results(self) -> list[dict]:
        """
        Retrieves all results from the 'Results' table.

        Returns:
            list[dict]: A list of dictionaries representing the results.
        """
        return self.client.table("Results").select('*').execute().data
  
    def download_file(self, path: str):
        """
        Downloads a file from the storage.

        Args:
            path (str): The path to the file in the format "bucket_name/source".

        Returns:
            Any: The result of the download operation, usually the file content.
        """
        bucket_name, source = path.split('/')
        res = self.client.storage.from_(bucket_name).download(source)
        return res
    
    def update_config_by_id(self, pipeline_id: str, config: dict):
        return self.client.table('Pipelines').update({"config": config}).eq("id", pipeline_id).execute().data[0]['id']
    
    def update_pipeline_name_by_id(self, pipeline_id: str, pipeline_name: str):
        return self.client.table('Pipelines').update({"name": pipeline_name}).eq("id", pipeline_id).execute().data[0]['id']