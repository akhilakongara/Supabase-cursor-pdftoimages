import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import base64

class DocumentManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def get_file_info(self, filepath):
        """Extract basic file information"""
        path = Path(filepath)
        stats = path.stat()
        return {
            'filename': path.name,
            'file_extension': path.suffix[1:],  # Remove the dot
            'file_type': self._determine_file_type(path.suffix),
            'size_kb': stats.st_size // 1024,
            'created_at': datetime.fromtimestamp(stats.st_ctime).isoformat(),
            'last_modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
        }
    
    def _determine_file_type(self, extension):
        """Map file extension to file type"""
        extension = extension.lower()
        type_mapping = {
            '.pdf': 'PDF',
            '.doc': 'Word',
            '.docx': 'Word',
            '.ppt': 'PowerPoint',
            '.pptx': 'PowerPoint'
        }
        return type_mapping.get(extension, 'Other')
    
    def process_document(self, filepath):
        """Main method to process a document"""
        if not os.path.exists(filepath):
            print(f"Error: File {filepath} not found!")
            return
            
        # Get file information
        file_info = self.get_file_info(filepath)
        
        # Create output directory if it doesn't exist
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        # Open PDF document
        doc = fitz.open(filepath)
        page_count = len(doc)
        
        # Get additional information from user
        author = input("Enter document author: ")
        title = input("Enter document title: ")
        description = input("Enter document description: ")
        version = input("Enter document version (press Enter for default 1.0): ") or "1.0"
        
        # Insert document record
        document_data = {
            'filename': file_info['filename'],
            'file_extension': file_info['file_extension'],
            'file_type': file_info['file_type'],
            'size_kb': file_info['size_kb'],
            'author': author,
            'description': description,
            'page_count': page_count,
            'title': title,
            'version': version
        }
        
        try:
            result = self.supabase.table('documents').insert(document_data).execute()
            document_id = result.data[0]['id']
            
            # Process each page
            base_filename = Path(filepath).stem
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap()
                output_path = output_dir / f"{base_filename}-p{page_num + 1}.jpg"
                pix.save(str(output_path))
                
                # Read the image file and convert to base64
                with open(output_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                
                # Insert page record
                page_data = {
                    'document_id': document_id,
                    'page_number': page_num + 1,
                    'page_image': img_data
                }
                
                self.supabase.table('document_pages').insert(page_data).execute()
                print(f"Processed page {page_num + 1} of {page_count}")
            
            doc.close()
            print(f"\nDocument processed successfully! Document ID: {document_id}")
            
        except Exception as e:
            print(f"Error processing document: {e}")
            doc.close()
            return False
        
        return True
    
    def list_documents(self):
        """List all documents in the database"""
        try:
            result = self.supabase.table('documents').select("*").execute()
            documents = result.data
            
            if not documents:
                print("\nNo documents found in the database.")
                return
            
            print("\nDocuments in the database:")
            print("-" * 80)
            for doc in documents:
                print(f"ID: {doc['id']}")
                print(f"Title: {doc['title']}")
                print(f"Author: {doc['author']}")
                print(f"Pages: {doc['page_count']}")
                print("-" * 80)
                
        except Exception as e:
            print(f"Error listing documents: {e}")

def display_menu():
    """Display the main menu"""
    print("\nDocument Management System")
    print("1. Upload new document")
    print("2. List all documents")
    print("3. Exit")
    return input("Select an option (1-3): ")

def main():
    manager = DocumentManager()
    
    while True:
        choice = display_menu()
        
        if choice == "1":
            filepath = input("\nPlease enter the path to your document: ")
            manager.process_document(filepath)
            
        elif choice == "2":
            manager.list_documents()
            
        elif choice == "3":
            print("\nExiting the program. Goodbye!")
            break
            
        else:
            print("\nInvalid option. Please try again.")

if __name__ == "__main__":
    main()
