import os
import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
import pandas as pd
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FlexcubeTestCaseGenerator:
    def __init__(self, qdrant_url, qdrant_api_key, collections):
        """
        Initialize Qdrant client, embedding model, and Groq client
        
        Args:
            qdrant_url (str): URL of Qdrant vector database
            qdrant_api_key (str): API key for Qdrant
            collections (list): List of Qdrant collection names
        """
        # Validate environment variables
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL")
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not self.qdrant_url or not self.qdrant_api_key or not self.groq_api_key:
            raise ValueError("Missing required environment variables: QDRANT_URL, QDRANT_API_KEY, or GROQ_API_KEY")

        # Using smaller embedding model with padding to 896 dimensions
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.original_dim = 384  # Dimension of all-MiniLM-L6-v2 embeddings
        self.target_dim = 896    # Target dimension for Qdrant
        
        # Qdrant client initialization
        self.qdrant_client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key
        )
        
        # Collections to search
        self.collection_names = collections
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=self.groq_api_key)

    def _pad_embeddings(self, embeddings):
        """
        Pad embeddings from original dimension to target dimension (896)
        
        Args:
            embeddings (np.array): Original embeddings
            
        Returns:
            list: Padded embeddings as list
        """
        if isinstance(embeddings, list):
            embeddings = np.array(embeddings)
            
        # Calculate padding needed
        pad_size = self.target_dim - self.original_dim
        
        if pad_size > 0:
            # Pad with zeros
            padded = np.pad(embeddings, (0, pad_size), mode='constant')
        else:
            padded = embeddings[:self.target_dim]  # Truncate if needed
            
        return padded.tolist()

    def semantic_search(self, query, top_k=5):
        """
        Perform semantic search across Flexcube user manual collections
        
        Args:
            query (str): Search query
            top_k (int): Number of top results to retrieve
        
        Returns:
            list: Retrieved context for test case generation
        """
        # Generate query embedding and pad to 896 dimensions
        query_embedding = self.embedding_model.encode(query)
        query_embedding = self._pad_embeddings(query_embedding)
        
        # Collect results from all collections
        all_results = []
        for collection in self.collection_names:
            search_results = self.qdrant_client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=top_k
            )
            all_results.extend(search_results)
        
        # Sort and get top results
        all_results.sort(key=lambda x: x.score, reverse=True)
        top_results = all_results[:top_k]
        
        # Extract and return context
        contexts = [result.payload.get('text', '') for result in top_results]
        return contexts

    def generate_test_scenarios(self, requirement):
        """
        Generate test scenarios and descriptions from the requirement
        
        Args:
            requirement (str): Initial requirement or function description
        
        Returns:
            list: Generated test scenarios with ID, type, scenario, and description
        """
        llm_prompt = f"""
        You are a professional software test engineer creating detailed test scenarios for Flexcube banking system.

        REQUIREMENT: {requirement}

        INSTRUCTIONS:
        1. Generate 10 comprehensive test scenarios covering all aspects of the requirement
        2. Include both positive and negative test scenarios
        3. Follow this exact output format for EACH test scenario:

        Test Case ID: TC_001
        Test Type: Positive/Negative
        Test Scenario: [Clear scenario description in one sentence]
        Test Case Description: [Detailed explanation of the test scenario]

        GENERATE 10 TEST SCENARIOS COVERING ALL ASPECTS OF THE REQUIREMENT.
        """

        try:
            chat_completion = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a professional software test engineer specializing in Flexcube testing."},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            llm_response = chat_completion.choices[0].message.content
            
            # Parse test scenarios
            return self._parse_test_scenarios(llm_response)
        
        except Exception as e:
            print(f"Error generating test scenarios: {e}")
            return []

    def _parse_test_scenarios(self, llm_response):
        """
        Parse LLM generated test scenarios
        
        Args:
            llm_response (str): Raw LLM response containing test scenarios
        
        Returns:
            list: Parsed test scenarios
        """
        test_scenarios = []
        
        # Split by Test Case ID
        case_splits = re.split(r'(Test Case ID:\s*TC_\d+)', llm_response)
        
        for i in range(1, len(case_splits), 2):
            try:
                full_case = case_splits[i] + (case_splits[i+1] if i+1 < len(case_splits) else '')
                
                def clean_text(text):
                    return text.replace('**', '').strip() if text else ''
                
                test_scenario = {
                    'Test Case ID': clean_text(re.search(r'Test Case ID:\s*(TC_\d+)', full_case).group(1) if re.search(r'Test Case ID:\s*(TC_\d+)', full_case) else f'TC_{i//2+1:03d}'),
                    'Test Type': clean_text(re.search(r'Test Type:\s*(\w+)', full_case).group(1) if re.search(r'Test Type:\s*(\w+)', full_case) else 'Unspecified'),
                    'Test Scenario': clean_text(re.search(r'Test Scenario:\s*(.+?)(?=\n|Test Case Description)', full_case).group(1) if re.search(r'Test Scenario:\s*(.+?)(?=\n|Test Case Description)', full_case) else 'No scenario'),
                    'Test Case Description': clean_text(re.search(r'Test Case Description:\s*(.+?)(?=\n\s*Test Case ID:|$)', full_case, re.DOTALL).group(1) if re.search(r'Test Case Description:\s*(.+?)(?=\n\s*Test Case ID:|$)', full_case, re.DOTALL) else 'No description')
                }
                
                test_scenarios.append(test_scenario)
            
            except Exception as e:
                print(f"Error parsing individual test scenario: {e}")
        
        return test_scenarios

    def generate_test_steps(self, test_scenario, test_description):
        """
        Generate test steps and expected results for a specific test scenario using retrieved context
        
        Args:
            test_scenario (str): Test scenario
            test_description (str): Test case description
        
        Returns:
            dict: Generated test steps and expected result
        """
        # Combine scenario and description for better context retrieval
        search_query = f"{test_scenario} {test_description}"
        
        # Retrieve relevant contexts from Qdrant
        contexts = self.semantic_search(search_query)
        context_str = "\n\n".join(contexts)
        
        llm_prompt = f"""
        You are a professional Flexcube test engineer creating detailed test steps.

        TEST SCENARIO: {test_scenario}
        TEST DESCRIPTION: {test_description}

        RETRIEVED FLEXCUBE CONTEXT: 
        {context_str}

        INSTRUCTIONS:
        1. Based on the test scenario, description, and retrieved Flexcube context, generate detailed test steps
        2. Create precise expected results that validate the test scenario
        3. Follow this exact output format:

        Test Steps:
        1. [First specific step with exact Flexcube navigation/action]
        2. [Second specific step]
        3. [Continue with additional steps as needed]

        Expected Result: [Precise expected outcome]

        GENERATE ONLY THE TEST STEPS AND EXPECTED RESULT. BE SPECIFIC TO FLEXCUBE NAVIGATION, SCREENS, AND FIELDS.
        """

        try:
            chat_completion = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a professional software test engineer specializing in Flexcube testing."},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            llm_response = chat_completion.choices[0].message.content
            
            # Parse test steps and expected result
            return self._parse_steps_and_result(llm_response)
        
        except Exception as e:
            print(f"Error generating test steps: {e}")
            return {"Test Steps": "Error generating steps", "Expected Result": "Error generating expected result"}

    def _parse_steps_and_result(self, llm_response):
        """
        Parse LLM generated test steps and expected result
        
        Args:
            llm_response (str): Raw LLM response
        
        Returns:
            dict: Parsed test steps and expected result
        """
        try:
            # Extract test steps
            steps_match = re.search(r'Test Steps:\s*(.+?)(?=Expected Result:|$)', llm_response, re.DOTALL)
            steps_text = steps_match.group(1).strip() if steps_match else "No steps provided"
            
            # Format test steps
            steps_lines = [line.strip() for line in steps_text.split('\n') if line.strip()]
            
            # Clean up numbering and ensure consistent format
            formatted_steps = []
            for i, step in enumerate(steps_lines):
                # Remove existing numbering if present
                clean_step = re.sub(r'^\s*\d+\.?\s*', '', step)
                if clean_step:
                    formatted_steps.append(f"{i+1}. {clean_step}")
            
            formatted_steps_text = "\n".join(formatted_steps)
            
            # Extract expected result
            result_match = re.search(r'Expected Result:\s*(.+?)$', llm_response, re.DOTALL)
            result_text = result_match.group(1).strip() if result_match else "No expected result provided"
            
            return {
                "Test Steps": formatted_steps_text,
                "Expected Result": result_text
            }
        
        except Exception as e:
            print(f"Error parsing test steps and expected result: {e}")
            return {
                "Test Steps": "Error parsing steps",
                "Expected Result": "Error parsing expected result"
            }

    def generate_flexcube_test_cases(self, requirement, output_path):
        """
        Full workflow to generate Flexcube test cases with two-step approach
        
        Args:
            requirement (str): Requirement description
            output_path (str): Path to save test cases
        
        Returns:
            pd.DataFrame: Generated test cases
        """
        print("Generating test scenarios and descriptions from requirement...")
        test_scenarios = self.generate_test_scenarios(requirement)
        
        # Complete test cases with test steps and expected results
        test_cases = []
        for i, scenario in enumerate(test_scenarios):
            print(f"Processing scenario {i+1}/{len(test_scenarios)}: {scenario['Test Scenario']}")
            
            # Get test steps and expected result for this specific scenario
            steps_and_result = self.generate_test_steps(
                scenario['Test Scenario'], 
                scenario['Test Case Description']
            )
            
            # Create complete test case
            test_case = {
                'Test Case ID': scenario['Test Case ID'],
                'Test Scenario': scenario['Test Scenario'],
                'Test Case Description': scenario['Test Case Description'],
                'Test Steps': steps_and_result['Test Steps'],
                'Expected Result': steps_and_result['Expected Result']
            }
            
            test_cases.append(test_case)
        
        # Convert to DataFrame
        test_cases_df = pd.DataFrame(test_cases)
        
        # Save test cases
        self.save_test_cases(test_cases_df, output_path)
        
        return test_cases_df

    def save_test_cases(self, df, output_path):
        """
        Save test cases to Excel with enhanced formatting
        
        Args:
            df (pd.DataFrame): Test cases DataFrame
            output_path (str): Path to save Excel file
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Flexcube Test Cases')
                
                worksheet = writer.sheets['Flexcube Test Cases']
                
                # Set column widths
                column_widths = {col: 40 for col in range(len(df.columns))}
                for col, width in column_widths.items():
                    worksheet.column_dimensions[chr(65 + col)].width = width
                
                # Style headers and cells
                from openpyxl.styles import Font, Alignment
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')

                # Also apply text wrapping and vertical center alignment to all data cells
                for row in worksheet.iter_rows(min_row=2):
                    for cell in row:
                        cell.alignment = Alignment(wrap_text=True, vertical='center')
            
            print(f"Test cases saved to: {output_path}")
        
        except Exception as e:
            print(f"Error saving test cases: {e}")
            raise e