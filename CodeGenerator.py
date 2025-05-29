import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import litellm
from litellm import completion, RateLimitError
import time

class CodeGenerator:
    def __init__(self, qdrant_url=None, qdrant_api_key=None, collections=None, groq_api_key=None):
        """Initialize the Code Generator service."""
        load_dotenv()
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL")
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.collections = collections or ["Sql_Database", "DDL_Database", "sql-embeddings_main2"]

        self.llm = self.LiteLLMGroqWrapper(api_key=self.groq_api_key)

        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Error initializing SentenceTransformer: {e}")
            self.model = None

    class LiteLLMGroqWrapper:
        def __init__(self, model="groq/llama-3.3-70b-versatile", api_key=None):
            self.model = model
            self.api_key = api_key

        def chat(self, messages, **kwargs):
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    api_key=self.api_key,
                    max_tokens=2048,
                    temperature=1.3,
                    **kwargs
                )
                return response['choices'][0]['message']['content']
            except litellm.RateLimitError as e:
                print(f"Rate limit error: {e}")
                return "The request exceeded the rate limit. Please try with a simpler query or try again later."
            except Exception as e:
                print(f"Error in LLM completion: {e}")
                return "Sorry, there was an error generating the code. Please try again with more detailed requirements."

    def search_relevant_code(self, query: str, n_results: int = 2):
        """Search for relevant code examples in Qdrant."""
        if not self.model:
            print("SentenceTransformer model not initialized. Returning empty results.")
            return []
        try:
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            query_vector = self.model.encode(query).tolist()
            existing_collections = {col.name for col in client.get_collections().collections}
            valid_collections = [col for col in self.collections if col in existing_collections]
            if not valid_collections:
                print(f"No valid collections found in Qdrant! Available: {existing_collections}")
                return []
            all_results = []
            try:
                search_results = client.search(
                    collection_name=valid_collections[0],
                    query_vector=query_vector,
                    limit=n_results
                )
                all_results.extend(search_results)
            except Exception as e:
                print(f"Error searching collection {valid_collections[0]}: {e}")
            return [result.payload for result in all_results if hasattr(result, 'payload')]
        except Exception as e:
            print(f"Error in search_relevant_code: {e}")
            return []

    def _extract_content_from_payload(self, payload):
        """Extract content from payload, prioritizing 'content' then 'text' fields."""
        if isinstance(payload, dict):
            if 'content' in payload and payload['content']:
                return str(payload['content'])
            elif 'text' in payload and payload['text']:
                return str(payload['text'])
            else:
                return str(payload)
        else:
            return str(payload)

    def run_crew(self, code_requirements):
        """
        Run the CrewAI workflow to generate, review, and improve PL/SQL code.
        Returns the final improved code or an error message.
        """
        print(f"Starting code generation for: {code_requirements}")
        if len(code_requirements) > 200:
            code_requirements = code_requirements[:200] + "..."

        requirements = {
            "type": "PL/SQL",
            "description": code_requirements
        }

        try:
            related_examples = self.search_relevant_code(f"PL/SQL {code_requirements}", 1)
            print(f"Found {len(related_examples)} related examples")
        except Exception as e:
            print(f"Error retrieving related examples: {e}")
            related_examples = []

        code_generator = Agent(
            role="Code Generator",
            goal="Generate clean and efficient PL/SQL code",
            backstory="You are a seasoned PL/SQL developer focused on writing optimal and reusable code with clear documentation.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

        code_reviewer = Agent(
            role="Code Reviewer",
            goal="Ensure PL/SQL code is correct, efficient, and aligned with best practices",
            backstory="You are a senior PL/SQL reviewer ensuring high code quality and adherence to standards.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

        code_improver = Agent(
            role="Code Improver",
            goal="Refine PL/SQL code by applying review feedback",
            backstory="You are a meticulous engineer focused on improving PL/SQL code quality through reviewer feedback.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

        try:
            # Step 1: Generate code
            task1 = self._code_gen_task_fn(requirements, related_examples, code_generator)
            crew1 = Crew(agents=[code_generator], tasks=[task1], verbose=True)
            gen_result = crew1.kickoff()
            print("Code generation completed")
            gen_result_str = str(gen_result)
            time.sleep(2)

            # Step 2: Review code
            task2 = self._review_task_fn(gen_result_str, code_reviewer)
            crew2 = Crew(agents=[code_reviewer], tasks=[task2], verbose=True)
            review_result = crew2.kickoff()
            print("Code review completed")
            review_result_str = str(review_result)
            time.sleep(2)

            # Step 3: Improve code
            task3 = self._improvement_task_fn(review_result_str, gen_result_str, code_improver)
            crew3 = Crew(agents=[code_improver], tasks=[task3], verbose=True)
            final_result = crew3.kickoff()
            print("Code improvement completed")
            final_result_str = str(final_result)

            formatted_result = self._format_final_result(final_result_str)
            return formatted_result
        except Exception as e:
            print(f"Error in run_crew: {e}")
            import traceback
            traceback.print_exc()
            return "/* Error generating code: The system encountered an issue processing your request. Please try with more detailed requirements or contact support. */"

    def _code_gen_task_fn(self, requirements, related_examples, agent):
        """Create code generation task with explicit required sections."""
        examples_text = ""
        if related_examples:
            examples_text = "Here's a related code example:\n\n"
            if related_examples and len(related_examples) > 0:
                example = related_examples[0]
                content = self._extract_content_from_payload(example)
                if len(content) > 1000:
                    content = content[:1000] + "..."
                examples_text += f"{content}\n\n"

        prompt = f"""
You are an expert PL/SQL developer. You must provide a structured answer with **ALL** of the following sections, starting each section on a new line with the exact header shown. If a section is not applicable, write 'None' after the header.

⚠️ WARNING: If you skip or omit any section or section header, your answer will be considered incomplete and rejected. Do NOT combine sections.

## REQUIRED SECTIONS AND ORDER

Intent of the Change:
[Describe the purpose and objective.]

Affected Code or Packages:
[List affected packages, modules, and database objects.]

Insertion Points:
[Specify where changes go (file, package, function, etc.).]

New Code:
[Provide the new or modified PL/SQL code for direct insertion.]

Invocation of new programming unit in existing source:
[Show a sample usage/call, or describe where it will be called.]

Explanation:
[Explain why this change is appropriate and meets the requirements.]

Required Import:
[List packages, grants, or dependencies. If none, write 'None'.]

## REQUIREMENTS
{requirements['description']}

{examples_text}
"""
        return Task(
            description=prompt,
            expected_output="A fully filled-out, structured answer with all seven sections above.",
            agent=agent
        )

    def _review_task_fn(self, code_output, agent):
        code_output_str = str(code_output)
        if len(code_output_str) > 1000:
            code_output_str = code_output_str[:1000] + "..."
        return Task(
            description=f"""Review the following PL/SQL code implementation:

{code_output_str}

Provide detailed suggestions for improvement, identify any logic or syntax issues, and recommend enhancements.

Respond with a list of issues (if any) and suggestions.
""",
            expected_output="Detailed review notes and improvement suggestions.",
            agent=agent
        )

    def _improvement_task_fn(self, review_notes, original_code, agent):
        review_notes_str = str(review_notes)
        original_code_str = str(original_code)

        if len(review_notes_str) > 100:
            review_notes_str = review_notes_str[:100] + "..."
        if len(original_code_str) > 2000:
            original_code_str = original_code_str[:2000] + "..."

        return Task(
            description=f"""Improve the original PL/SQL implementation by applying the following reviewer feedback:

Review:
{review_notes_str}

Code:
{original_code_str}

RESPONSE FORMAT:
Intent of the Change:
[Your answer]

Affected Code or Packages:
[Your answer]

Insertion Points:
[Your answer]

New Code:
[improved code]

Invocation of new programming unit in existing source:
[Your answer]

Explanation:
[explanation for the changes]

Required Import:
[package or dependency, if any]
""",
            expected_output="Refined PL/SQL implementation in structured format.",
            agent=agent
        )

    def _format_final_result(self, result):
        """Ensure all required sections are present, otherwise return a clear error."""
        required_sections = [
            "Intent of the Change:",
            "Affected Code or Packages:",
            "Insertion Points:",
            "New Code:",
            "Invocation of new programming unit in existing source:",
            "Explanation:",
            "Required Import:"
        ]
        result_str = str(result)
        missing = []
        for section in required_sections:
            if section not in result_str:
                print(f"WARNING: Section '{section}' missing from result.")
                missing.append(section)
        if missing:
            return (
                f"/* Error: The following sections are missing from the generated result: "
                f"{', '.join(missing)}. Please retry. */\n\n{result_str}"
            )
        return result_str