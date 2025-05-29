from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from waitress import serve
from io import BytesIO
import tempfile
import os
import sys
import subprocess
from dotenv import load_dotenv

# Import the generators
from FunctionDocumentGenerator import FunctionDocumentGenerator
from FlexcubeTestCaseGenerator import FlexcubeTestCaseGenerator
from CodeGenerator import CodeGenerator
from STDCIF import GenerateSTDCIF
from STDCUSAC import GenerateSTDCUSAC  

# Load environment variables
load_dotenv()

# Increase recursion limit (if needed)
sys.setrecursionlimit(3000)

app = Flask(__name__, static_folder=r"E:\FSD\word-doc-generator\my-react-app\dist", static_url_path="/")
CORS(app)

@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

# Qdrant and API configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Validate environment variables
if not QDRANT_URL or not QDRANT_API_KEY or not GROQ_API_KEY:
    print("Error: Missing required environment variables (QDRANT_URL, QDRANT_API_KEY, or GROQ_API_KEY).")
    sys.exit(1)

LOGO_PATH = r'E:\FSD\word-doc-generator\jmr new logo.png'

# Initialize generators
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

# Initialize the code generator
code_generator = CodeGenerator(
    qdrant_url=QDRANT_URL,
    qdrant_api_key=QDRANT_API_KEY,
    collections=["Sql_Database", "DDL_Database"],
    groq_api_key=GROQ_API_KEY
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

@app.route('/generate-test-cases', methods=['POST'])
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

@app.route('/generate-stdcif', methods=['POST'])
def generate_stdcif():
    data = request.json
    count = int(data.get('count', 50))
    
    try:
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "STDCIF_Cases.xlsx")
        master_file_path = r"E:\FSD\word-doc-generator\masterfile.xlsx"
        
        # Verify master file exists
        if not os.path.exists(master_file_path):
            return {"error": f"Master file not found at {master_file_path}"}, 400
        
        print(f"Generating {count} STDCIF test cases")
        print(f"Output path: {output_path}")
        print(f"Master file: {master_file_path}")
        
        success = GenerateSTDCIF.generate_excel(master_file_path, output_path, count)
        
        if not success:
            raise Exception("Failed to generate STDCIF test cases")
        
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file was not created at {output_path}")
        
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
    count = int(data.get('count', 10))
   
    try:
        # Generate a temporary file path for the Excel file
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "STDCUSAC_Cases.xlsx")
        master_file_path = r"E:\FSD\word-doc-generator\masterfile.xlsx"
       
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

# Run the Flask app
if __name__ == '__main__':
    # Use port 8080 to match frontend expectations
    app.run(debug=True, host='0.0.0.0', port=8080)