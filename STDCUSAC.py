import pandas as pd
import random
import string
import os
from datetime import datetime
import argparse
import names  # We'll use this library for generating random names

class GenerateSTDCUSAC:
    @staticmethod
    def generate_test_cases(count, master_file_path):
        # List of all columns
        all_columns = [
            "Test Case Id", "Test Id", "Linked Test Case Id", "Posting Branch", "Action",
            "CustomerNumber", "Currency", "AccountClass", "MainTab", "AccountType",
            "ModeOfOperation", "ATM", "AccountOpeningAmount", "Location", "Media",
            "PayInOption", "OffsetAccount", "WaiverAccountOpeningCharge", "IBANRequired",
            "SalaryAccount", "AuxillaryTab", "ATMAccountNumber", "AutoProvisioningRequired",
            "ExposureCategory", "ProvisionBtn", "ProvisioningStatus", "ProvisioningPercent",
            "DailyAmountLimit", "DailyCountLimit", "PostingAllowed", "NoDebits", "NoCredits",
            "StatusChangeAutomatic", "BackPeriodEntryAllowed", "TrackReceiveable",
            "ProjectAccount", "NomineeTab", "NewRecord", "Name", "RelationShip", "Address1",
            "Address2", "Address3", "Address4", "CheckListTab", "DocumentType", "Mandatory",
            "ExpiryDate", "ExpectedDateofSubmission", "ActualDateofSubmission",
            "DocumentReference", "JointHolderSubTab", "AddNewRecord", "CustomerNumber1",
            "CustomerName1", "JoiningStartDate", "JoiningEndDate", "JointHolderType",
            "MISTab", "PoolCode", "Save"
        ]
        
        # Load branch names from master file
        try:
            master_df = pd.read_excel(master_file_path)
            branch_names = master_df["Posting Branch"].tolist()  # Adjust column name as needed
            print(f"Successfully loaded {len(branch_names)} branch names from {master_file_path}")
        except Exception as e:
            print(f"Error loading master file: {e}")
            print("Using default branch names instead")
            # Default branch names as fallback
            branch_names = ["001", "002", "003", "004", "005"]
        
        # List of street types for random address generation
        street_types = ["St", "Ave", "Blvd", "Rd", "Ln", "Dr", "Way", "Pl", "Ct"]
        
        # City names for random address generation
        city_names = ["Springfield", "Riverside", "Georgetown", "Franklin", "Clinton", 
                    "Arlington", "Fairview", "Salem", "Madison", "Washington", 
                    "Kingston", "Oxford", "Bristol", "Manchester", "Dover"]
        
        relation_types = [
            "FATHER", "MOTHER", "SPOUSE", "BROTHER", "SISTER",
            "SON", "DAUGHTER", "UNCLE", "AUNT", "COUSIN"
        ]
    
        # Generate data for each test case
        data = []
        for i in range(1, count + 1):
            test_case = {}
        
            # Initialize all columns to blank
            for col in all_columns:
                test_case[col] = ""
        
            # Fill in the required columns according to specifications
            test_case["Test Case Id"] = f"TS_ST_01_TC{i:02d}"
            test_case["Posting Branch"] = f"00{random.choice(branch_names)}" if branch_names else f"00{random.randint(1, 9)}"
            test_case["Action"] = "NEW"
            test_case["CustomerNumber"] = f"000{random.randint(100, 999)}"
            test_case["Currency"] = "EPG"
            test_case["AccountClass"] = random.choice(["SAVACC", "CURRACC", "STAFFACC"])
            test_case["MainTab"] = "YES"
            test_case["AccountType"] = "Single"
            test_case["ModeOfOperation"] = "Single"
            test_case["ATM"] = "YES"
            test_case["Location"] = "EG"
            test_case["Media"] = "MAIL"
            test_case["AuxillaryTab"] = "YES"
            test_case["ATMAccountNumber"] = ""  # Always blank
            test_case["AutoProvisioningRequired"] = "YES"
            test_case["ExposureCategory"] = random.choice(["EXPOSURE_CATEGORY", ""])
        
            # ProvisionBtn logic
            provision_btn = random.choice(["YES", ""])
            test_case["ProvisionBtn"] = provision_btn
            if provision_btn == "YES":
                test_case["ProvisioningStatus"] = "NORM"
                test_case["ProvisioningPercent"] = "100"
        
            # NomineeTab logic
            nominee_tab = random.choice(["YES", ""])
            test_case["NomineeTab"] = nominee_tab
            if nominee_tab == "YES":
                # Generate random name
                test_case["Name"] = names.get_full_name()
                test_case["RelationShip"] = random.choice(relation_types)
                
                # Generate random address
                street_num = random.randint(1, 9999)
                street_name = random.choice(string.ascii_uppercase) + ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
                street_type = random.choice(street_types)
                city = random.choice(city_names)
                zip_code = f"{random.randint(10000, 99999)}"
                
                test_case["Address1"] = f"{street_num} {street_name} {street_type}, {city}, {zip_code}"
        
            test_case["MISTab"] = "YES"
            test_case["PoolCode"] = "DFLTPOOL"
        
            data.append(test_case)
    
        return pd.DataFrame(data)
    
    @staticmethod
    def save_to_excel(df, file_path):
        """Save DataFrame to Excel with proper error handling"""
        try:
            # Create directory if needed and possible
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not create directory {dir_path}: {e}")
                    print("Proceeding with save attempt anyway...")
        
            # Try to save the file
            df.to_excel(file_path, index=False)
            print(f"Test cases successfully saved to {file_path}")
            return True
        except PermissionError:
            print(f"Error: Permission denied when saving to {file_path}")
            print("Please check if you have write access to this location or if the file is already open.")
            return False
        except Exception as e:
            print(f"Error saving file to {file_path}: {e}")
            return False

# # If the script is run directly (for testing)
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description='Generate STDCUSAC test cases in Excel format')
#     parser.add_argument('--count', type=int, default=10, help='Number of test cases to generate')
#     parser.add_argument('--output', type=str, default='STDCUSAC_Cases.xlsx', help='Output file path')
#     parser.add_argument('--master', type=str, default='masterfile.xlsx', help='Path to master file with branch names')
#     args = parser.parse_args()
    
#     # Generate test cases
#     df = GenerateSTDCUSAC.generate_test_cases(args.count, args.master)
    
#     # Save to Excel
#     GenerateSTDCUSAC.save_to_excel(df, args.output)