import pandas as pd
import random
import string
import datetime
from faker import Faker
import os
import re
import sys
import time

class GenerateSTDCIF:
    # Initialize Faker with Arabic (Egypt) locale for culturally appropriate names
    fake = Faker('ar_EG')  # Use Egyptian Arabic locale for realistic names

    @staticmethod
    def read_master_data(file_path):
        try:
            if not os.path.exists(file_path):
                print(f"Error: Master file not found at {file_path}")
                return None
            
            master_df = pd.read_excel(file_path)
            print(f"Successfully loaded master data from {file_path} with {len(master_df)} records")
            
            required_columns = ['CustomerNumber', 'Posting Branch']
            missing_columns = [col for col in required_columns if col not in master_df.columns]
            if missing_columns:
                print(f"Error: Missing required columns in master file: {missing_columns}")
                return None
            
            master_df['CustomerNumber'] = master_df['CustomerNumber'].astype(str)
            master_df['Posting Branch'] = master_df['Posting Branch'].astype(str)
            
            valid_master_df = master_df.dropna(subset=required_columns)
            valid_count = len(valid_master_df)
            print(f"Found {valid_count} valid rows with non-null CustomerNumber and Posting Branch")
            
            if valid_count < 5:
                print(f"Error: Master file has only {valid_count} valid rows, need at least 5 for copy cases")
                return None
            
            invalid_numbers = valid_master_df[~valid_master_df['CustomerNumber'].str.match(r'^\d{1,3}$')]
            if not invalid_numbers.empty:
                print(f"Warning: Found {len(invalid_numbers)} CustomerNumber values not in 1-3 digit format:")
                print(invalid_numbers[['CustomerNumber', 'Posting Branch']].head().to_string())
            
            invalid_branches = valid_master_df[~valid_master_df['Posting Branch'].str.match(r'^\d{1,3}$')]
            if not invalid_branches.empty:
                print(f"Warning: Found {len(invalid_branches)} Posting Branch values not in 1-3 digit format:")
                print(invalid_branches[['CustomerNumber', 'Posting Branch']].head().to_string())
            
            print(f"Raw master file content from {file_path} (first {min(10, len(master_df))} rows):")
            print(master_df.head(10)[['CustomerNumber', 'Posting Branch']].to_string())
            
            print("Sample customer number & posting branch pairs from valid rows:")
            for _, row in valid_master_df.head(5).iterrows():
                print(f"  CustomerNumber: {row['CustomerNumber']}, Posting Branch: {row['Posting Branch']}")
            
            return valid_master_df
        except Exception as e:
            print(f"Error loading master data from {file_path}: {e}")
            print("Cannot proceed without valid master data for copy cases")
            return None

    @staticmethod
    def random_alphanumeric(length):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    @staticmethod
    def random_mobile():
        return ''.join(random.choice(string.digits) for _ in range(10))

    @staticmethod
    def random_email():
        return GenerateSTDCIF.fake.email()

    @staticmethod
    def determine_gender(name):
        if name[-1].lower() in ['a', 'e', 'i']:
            return 'Female'
        else:
            return 'Male'

    @staticmethod
    def generate_test_case_id(index):
        return f"TS_ST_01_TC{str(index+1).zfill(2)}"

    @staticmethod
    def generate_fallback_data(customer_category):
        # Generate realistic names using Faker
        if customer_category == 'BANK':
            # For BANK, use a company name (institution-like)
            full_name = GenerateSTDCIF.fake.company()[:15]  # Limit to 15 chars to avoid overly long names
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0][:10]
                last_name = name_parts[-1][:10]  # Use last word of company name
            else:
                first_name = name_parts[0][:10]
                last_name = name_parts[0][:10]  # Fallback to same as first name if single word
        else:
            # For INDIVIDUAL or COMMERCIAL, generate a full name and split
            full_name = GenerateSTDCIF.fake.name()[:15]  # Limit to 15 chars
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0][:10]
                last_name = name_parts[-1][:10]
            else:
                first_name = name_parts[0][:10]
                last_name = GenerateSTDCIF.fake.last_name()[:10]
        
        gender = GenerateSTDCIF.determine_gender(first_name)
        address = GenerateSTDCIF.fake.address()[:30]  # Limit to 30 characters
        dob = GenerateSTDCIF.fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%m/%d/%Y')
        birth_place = random.choice(["Cairo", "Alexandria", "Giza", "Luxor", "Aswan"])
        
        return {
            "FullName": full_name,
            "FirstName": first_name,
            "LastName": last_name,
            "Gender": gender,
            "Address": address,
            "BirthDate": dob,
            "BirthPlace": birth_place
        }

    @staticmethod
    def generate_customer_data(is_new, index, master_data=None, copy_case_index=0):
        customer_category = random.choice(['INDIVIDUAL', 'COMMERCIAL', 'BANK'])
        
        data = GenerateSTDCIF.generate_fallback_data(customer_category)
        
        # Initialize variables
        posting_branch = ""
        customer_number = ""
        
        if is_new:
            customer_number = f"000{random.randint(0, 999):03d}"
            if master_data is not None and not master_data.empty:
                valid_branches = master_data['Posting Branch'].dropna().astype(str).tolist()
                if valid_branches:
                    posting_branch = random.choice(valid_branches)
                    try:
                        posting_branch = f"{int(posting_branch):03d}"
                    except (ValueError, TypeError):
                        posting_branch = posting_branch[:3].zfill(3)
                else:
                    posting_branch = f"{random.randint(1, 999):03d}"
            else:
                posting_branch = f"{random.randint(1, 999):03d}"
            print(f"New case {index+1}: Generated CustomerNumber {customer_number} with Posting Branch {posting_branch}")
        else:
            if master_data is not None and not master_data.empty:
                master_index = copy_case_index % len(master_data)
                master_record = master_data.iloc[master_index]
                raw_customer_number = str(master_record['CustomerNumber'])
                try:
                    customer_number = f"000{int(raw_customer_number):03d}"
                except (ValueError, TypeError):
                    customer_number = f"000{raw_customer_number.zfill(3)}"[:6]
                
                posting_branch = str(master_record['Posting Branch'])
                try:
                    posting_branch = f"{int(posting_branch):03d}"
                except (ValueError, TypeError):
                    posting_branch = posting_branch[:3].zfill(3)
                
                print(f"Copy case {index+1}: Selected CustomerNumber {customer_number} (raw: {raw_customer_number}) with Posting Branch {posting_branch} from master file")
            else:
                customer_number = f"000{random.randint(0, 999):03d}"
                posting_branch = f"{random.randint(1, 999):03d}"
                print(f"Copy case {index+1}: No valid master data, generated CustomerNumber {customer_number} with Posting Branch {posting_branch}")
        
        # Use the names from fallback
        full_name = data.get("FullName", GenerateSTDCIF.fake.name()[:15])
        first_name = data.get("FirstName", full_name.split()[0][:10])
        last_name = data.get("LastName", 'Bank' if customer_category == 'BANK' else full_name.split()[-1][:10])
        gender = data.get("Gender", GenerateSTDCIF.determine_gender(first_name))
        address = data.get("Address", GenerateSTDCIF.fake.address()[:30])
        dob = data.get("BirthDate", GenerateSTDCIF.fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%m/%d/%Y'))
        birth_place = data.get("BirthPlace", random.choice(["Cairo", "Alexandria", "Giza", "Luxor", "Aswan"]))
        
        # Generate ShortName from FullName
        base_short_name = ''.join(c for c in full_name if c.isalnum())[:7]
        short_name = f"{base_short_name[:7]}{str(index+1).zfill(3)}".ljust(10, '0')[:10]
        
        # Generate EmailID with @gmail.com
        email_local_part = ''.join(c for c in full_name if c.isalnum()).lower()[:20]  # Limit to 20 chars
        email_id = f"{email_local_part}@gmail.com"
        
        # Generate data dictionary
        data = {
            "RunMode": "Yes",
            "ScreenName": "Customer",
            "Test Scenario": "Create Customer",
            "Test Case Id": GenerateSTDCIF.generate_test_case_id(index),
            "Test Id": "",
            "Linked Test Case Id": "",
            "Posting Branch": posting_branch,
            "Action": "New" if is_new else "Copy",
            "Type": random.choice(["Individual", "Corporate", "Bank"]),
            "CustomerNumber": customer_number,
            "CustomerCategory": customer_category,
            "PrivateCustomer": "No" if is_new else "",
            "FullName": full_name,
            "ShortName": short_name,
            "KYCStatus": "Yet to verify" if is_new else "",
            "KYCReferenceNumber": "",
            "DowJonesQueryReferenceNo": "",
            "Prefix": "",
            "FirstName": first_name,
            "LastName": last_name,
            "MiddleName": "",
            "WorkPhoneISD": "",
            "WorkPhone": "",
            "MobileISDCode": "",
            "MobileNumber": GenerateSTDCIF.random_mobile(),
            "EmailID": email_id,
            "Gender": gender,
            "BirthCountry": "EG",
            "BirthPlace": birth_place,
            "Nationality": "EG",
            "FaxISDCode": "",
            "CommunicationMode": "",
            "Address1Corres": address,
            "Address2Corres": "",
            "Address3Corres": "",
            "Address4Corres": "",
            "CountyCorres": "",
            "CountryCorres": "EG",
            "AddressName": address,
            "SameAsCorresAddress": "Yes",
            "AddressCode": "",
            "Address1": "",
            "Address2": "",
            "Address3": "",
            "Address4": "",
            "ResidenceStatus": "Resident",
            "Mother'sMaidenName": "",
            "SubmitAgeProof": "",
            "PreferredDateOfContact": "",
            "PreferredTimeOfContact": "",
            "JointCheckbox": "",
            "JointTab": "No",
            "JointGender": "",
            "JointFirstName": "",
            "JointLastName": "",
            "JointAddress1": "",
            "JointAddress2": "",
            "JointAddress3": "",
            "JointDOB": "",
            "JointResidentStatus": "",
            "JointDeceased": "",
            "Country": "",
            "Language": "Arab",
            "Address": "",
            "DateofBirth": dob,
            "CommunicationMode": "",
            "JointCustomer": "",
            "JointGender": "",
            "JointFirstName": "",
            "JointLastName": "",
            "ADDITIONAL_TAB": "Yes",
            "Exposure": "",
            "Location": "EG",
            "Media": "Mail",
            "ChargeGroup": "",
            "SameAsAddress": "Yes",
            "IdentifierName": "",
            "IdentifierValue": "",
            "AUXILARY_TAB": "No",
            "BusinessUDF": "",
            "LimitTab": "No",
            "OverallLimit": "",
            "FieldTab": "Yes",
            "RelatedParty": "Yes",
            "CHECKLIST_TAB": "No",
            "Checkaddbutton": "",
            "DOCUMENT_CATEGORY": "",
            "DOCUMENT_TYPE": "",
            "DOCUMENT_NAME": "",
            "DOCUMENT_REFERENCE": "",
            "DATE_REQUESTED": "",
            "EXPECTED_DATE": "",
            "ACTUAL_DATE": "",
            "EXPIRY_DATE": "",
            "REMARKS": "",
            "CHECK": "",
            "GroupTab": "No",
            "PartnershipDetails": "",
            "ShareHolderId": "",
            "HoldingPercentage": "",
            "MIS": "No",
            "MIS_Code": "",
            "Save": "Yes"
        }
        
        return data

    @staticmethod
    def generate_test_data(count, master_data=None):
        data = []
        
        # Calculate number of new and copy cases
        new_cases = max(int(count * 0.8), 1)  # 80% new cases, at least 1
        copy_cases = count - new_cases  # Remaining are copy cases
        
        print(f"Generating {new_cases} new test cases...")
        for i in range(new_cases):
            data.append(GenerateSTDCIF.generate_customer_data(is_new=True, index=i, master_data=master_data))
        
        print(f"Generating {copy_cases} copy test cases...")
        for i in range(new_cases, count):
            copy_case_index = i - new_cases
            data.append(GenerateSTDCIF.generate_customer_data(is_new=False, index=i, master_data=master_data, copy_case_index=copy_case_index))
        
        return data

    @staticmethod
    def generate_excel(master_file, output_file, count):
        """Generate STDCIF test cases and save to Excel"""
        print(f"Using master data file: {master_file}")
        print(f"Output will be saved to: {output_file}")
        
        master_data = GenerateSTDCIF.read_master_data(master_file)
        if master_data is None:
            print("Failed to load master data. Exiting.")
            return False
        
        print(f"Generating {count} test cases...")
        test_data = GenerateSTDCIF.generate_test_data(count, master_data)
        df = pd.DataFrame(test_data)
        
        all_columns = [
            "Test Case Id", "Test Id", "Linked Test Case Id",
            "Posting Branch", "Action", "Type", "CustomerNumber", "CustomerCategory", "PrivateCustomer",
            "FullName", "ShortName", "KYCStatus", "KYCReferenceNumber", "DowJonesQueryReferenceNo",
            "Prefix", "FirstName", "LastName", "MiddleName", "WorkPhoneISD", "WorkPhone", "MobileISDCode",
            "MobileNumber", "EmailID", "Gender", "BirthCountry", "BirthPlace", "Nationality", "FaxISDCode",
            "CommunicationMode", "Address1Corres", "Address2Corres", "Address3Corres", "Address4Corres",
            "CountyCorres", "CountryCorres", "AddressName", "SameAsCorresAddress", "AddressCode",
            "Address1", "Address2", "Address3", "Address4", "ResidenceStatus", "Mother'sMaidenName",
            "SubmitAgeProof", "PreferredDateOfContact", "PreferredTimeOfContact", "JointCheckbox",
            "JointTab", "JointGender", "JointFirstName", "JointLastName", "JointAddress1", "JointAddress2",
            "JointAddress3", "JointDOB", "JointResidentStatus", "JointDeceased", "Country", "Language",
            "Address", "DateofBirth", "CommunicationMode", "JointCustomer", "JointGender", "JointFirstName",
            "JointLastName", "ADDITIONAL_TAB", "Exposure", "Location", "Media", "ChargeGroup",
            "SameAsAddress", "IdentifierName", "IdentifierValue", "AUXILARY_TAB", "BusinessUDF",
            "LimitTab", "OverallLimit", "FieldTab", "RelatedParty", "CHECKLIST_TAB", "Checkaddbutton",
            "DOCUMENT_CATEGORY", "DOCUMENT_TYPE", "DOCUMENT_NAME", "DOCUMENT_REFERENCE",
            "DATE_REQUESTED", "EXPECTED_DATE", "ACTUAL_DATE", "EXPIRY_DATE", "REMARKS", "CHECK",
            "GroupTab", "PartnershipDetails", "ShareHolderId", "HoldingPercentage", "MIS", "MIS_Code", "Save"
        ]
        
        df = df.reindex(columns=all_columns)
        df.to_excel(output_file, index=False)
        
        print(f"Generated {len(test_data)} test cases and saved to {output_file}")
        return True

# if __name__ == "__main__":
#     master_file=r"C:\Users\166\Desktop\FSD\word-doc-generator\masterfile.xlsx"
#     output_file=r"C:\Users\166\Desktop\FSD\STDCIF_Cases.xlsx"
#     count=100
#     GenerateSTDCIF.generate_excel(master_file, output_file, count)

