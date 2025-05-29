from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from waitress import serve
from io import BytesIO
import tempfile
import os
import sys
import subprocess

# Import all generators
from FunctionDocumentGenerator import FunctionDocumentGenerator
from FlexcubeTestCaseGenerator import FlexcubeTestCaseGenerator
from CodeGenerator import CodeGenerator
from STDCIF import GenerateSTDCIF
from STDCUSAC import GenerateSTDCUSAC

# Increase recursion limit (if needed)
sys.setrecursionlimit(3000)

app = Flask(__name__, static_folder=r"D:\FSD\word-doc-generator\dist", static_url_path="/")
CORS(app)

@app.route("/", methods=["GET"])
def serve_index():
    """Serve the main index.html page"""
    return send_from_directory(app.static_folder, "index.html")

# Qdrant and API configuration
QDRANT_URL = "https://400b0838-1c66-42c4-93d2-1e8de90a6437.us-west-2-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "TBLxMZj3nWHKwDolq45O9UCo5r4mItvMZpNNj_H30aSyibdX1qJCdQ"
LOGO_PATH = r'D:\FSD\word-doc-generator\jmr new logo.png'

# Initialize all generators
function_doc_generator = FunctionDocumentGenerator(
    qdrant_url=QDRANT_URL,
    qdrant_api_key=QDRANT_API_KEY,
    collections=["Flexcube_user_guide_14.x", "Flexcube_Userguide_12.x"]
)

test_case_generator = FlexcubeTestCaseGenerator(
    qdrant_url=QDRANT_URL,
    qdrant_api_key=QDRANT_API_KEY,
    collections=["Flexcube_user_guide_14.x", "Flexcube_Userguide_12.x", "fn_tables2"]
)

code_generator = CodeGenerator(
    qdrant_url=QDRANT_URL,
    qdrant_api_key=QDRANT_API_KEY,
    collections=["Sql_Database", "DDL_Database"],
    groq_api_key=os.getenv("GROQ_API_KEY")
)

@app.route('/generate-doc', methods=['POST'])
def generate_doc():
    """
    API endpoint to generate and download the Word document.
    """
    data = request.json
    user_input = data.get('text', '')

    if not user_input:
        return {"error": "No input provided"}, 400

    try:
        # Generate the document content
        document_content = function_doc_generator.generate_function_document(user_input)
        
        # Get the document object
        doc_obj = function_doc_generator.save_as_word(document_content, logo_path=LOGO_PATH)
        
        if not doc_obj:
            return {"error": "Failed to generate document"}, 500
        
        # Save the document to a BytesIO object
        file_stream = BytesIO()
        doc_obj.save(file_stream)
        file_stream.seek(0)
        
        # Generate a filename based on the first few words of the requirement
        words = user_input.split()[:3]
        filename = "_".join(words).lower().replace(" ", "_")[:30]
        filename = f"function_spec_{filename}.docx"
        
        # Send the file directly to the user
        return send_file(
            file_stream,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            download_name=filename,
            as_attachment=True
        )
        
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}, 500

@app.route('/generate-testcases', methods=['POST'])
def generate_test_cases():
    """
    API endpoint to generate and download the test cases Excel file.
    """
    data = request.json
    user_input = data.get('text', '')
    if not user_input:
        return {"error": "No input provided"}, 400
    try:
        # Generate a temporary file path for the Excel file
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "test_cases.xlsx")
        
        # Generate test cases
        test_cases_df = test_case_generator.generate_flexcube_test_cases(user_input, output_path)
        
        # Return the file to the client
        return send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='test_cases.xlsx',
            as_attachment=True
        )
        
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}, 500

@app.route('/generate-code', methods=['POST'])
def generate_code():
    """
    API endpoint to generate PL/SQL code based on requirements.
    """
    data = request.json
    user_input = data.get('text', '')
    
    if not user_input:
        return {"error": "No input provided"}, 400
    
    try:
        # Generate the code using the CrewAI workflow
        code_result = code_generator.run_crew(user_input)
        
        # Return the code generation result
        return jsonify({
            "success": True,
            "result": code_result
        })
        
    except Exception as e:
        print(f"Error in code generation: {e}")
        return {"error": str(e)}, 500

@app.route('/generate-stdcif', methods=['POST'])
def generate_stdcif():
    """API endpoint to generate and download STDCIF test cases Excel file."""
    data = request.json
    count = int(data.get('count', 50))  # Convert to integer, default to 50 if not specified
    
    try:
        # Generate a temporary file path for the Excel file
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "STDCIF_Cases.xlsx")
        master_file_path = r"D:\FSD\word-doc-generator\masterfile.xlsx"
        
        # Log the parameters for debugging
        print(f"Generating {count} STDCIF test cases")
        print(f"Output path: {output_path}")
        print(f"Master file: {master_file_path}")
        
        # Directly call the generate_excel method
        success = GenerateSTDCIF.generate_excel(master_file_path, output_path, count)
        
        if not success:
            raise Exception("Failed to generate STDCIF test cases")
        
        # Check if the file was created
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file was not created at {output_path}")
        
        # Return the file to the client
        return send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='STDCIF_Cases.xlsx',
            as_attachment=True
        )
    
    except Exception as e:
        print(f"Error generating STDCIF test cases: {e}")
        return {"error": str(e)}, 500

@app.route('/generate-stdcusac', methods=['POST'])
def generate_stdcusac():
    """API endpoint to generate and download STDCUSAC test cases Excel file."""
    data = request.json
    count = int(data.get('count', 10))  # Convert to integer, default to 10 if not specified
   
    try:
        # Generate a temporary file path for the Excel file
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "STDCUSAC_Cases.xlsx")
        master_file_path = r"D:\FSD\word-doc-generator\masterfile.xlsx"
       
        # Log the parameters for debugging
        print(f"Generating {count} STDCUSAC test cases")
        print(f"Output path: {output_path}")
        print(f"Master file: {master_file_path}")
       
        # First generate the test cases DataFrame
        df = GenerateSTDCUSAC.generate_test_cases(count, master_file_path)
        
        # Then save the DataFrame to Excel
        success = GenerateSTDCUSAC.save_to_excel(df, output_path)
       
        if not success:
            raise Exception("Failed to save STDCUSAC test cases to Excel")
       
        # Check if the file was created
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file was not created at {output_path}")
       
        # Return the file to the client
        return send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='STDCUSAC_Cases.xlsx',
            as_attachment=True
        )
   
    except Exception as e:
        print(f"Error generating STDCUSAC test cases: {e}")
        return {"error": str(e)}, 500

# Run the Flask app
if __name__ == '__main__':
    app.run(host="192.168.2.95", port=8080, debug=True)