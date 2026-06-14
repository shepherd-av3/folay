from flask import Flask, redirect, request, session, render_template, jsonify, url_for
from supabase import create_client
import os
import uuid
from datetime import datetime
import base64
import qrcode
from io import BytesIO
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "mylegaldocs_supersecret_key_2024_kenya"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ==================== LEGAL DOCUMENT CATEGORIES ====================
DOCUMENT_CATEGORIES = {
    "birth_early": {
        "name": "BIRTH & EARLY REGISTRATION",
        "icon": "👶",
        "order": 1,
        "documents": [
            {"id": "birth_certificate", "name": "Birth Certificate", "required": True, "fields": ["document_number", "issue_date", "full_name", "date_of_birth", "place_of_birth", "mother_name", "father_name"]},
            {"id": "immunization_card", "name": "Immunization Card", "required": False, "fields": ["document_number", "issue_date", "full_name", "hospital_name"]},
            {"id": "birth_notification", "name": "Birth Notification", "required": True, "fields": ["document_number", "issue_date", "full_name", "hospital_name"]}
        ]
    },
    "childhood_school": {
        "name": "CHILDHOOD & SCHOOL RECORDS",
        "icon": "📚",
        "order": 2,
        "documents": [
            {"id": "kcpe_certificate", "name": "KCPE Certificate", "required": True, "fields": ["document_number", "issue_date", "school_name", "full_name", "candidate_index", "total_marks"]},
            {"id": "kcse_certificate", "name": "KCSE Certificate", "required": True, "fields": ["document_number", "issue_date", "school_name", "full_name", "candidate_index", "mean_grade"]},
            {"id": "school_leaving", "name": "School Leaving Certificate", "required": False, "fields": ["document_number", "issue_date", "school_name", "full_name"]},
            {"id": "primary_school_report", "name": "Primary School Reports", "required": False, "fields": ["school_name", "full_name", "class_name", "academic_year"]}
        ]
    },
    "identity": {
        "name": "ADULT IDENTITY DOCUMENTS",
        "icon": "🆔",
        "order": 3,
        "documents": [
            {"id": "national_id", "name": "National ID Card", "required": True, "fields": ["document_number", "issue_date", "full_name", "date_of_birth", "id_serial_number", "place_of_issue"]},
            {"id": "passport", "name": "Passport", "required": False, "fields": ["document_number", "issue_date", "expiry_date", "full_name", "passport_type", "country_of_issue"]},
            {"id": "kra_pin", "name": "KRA PIN Certificate", "required": True, "fields": ["kra_pin", "issue_date", "full_name", "pin_status", "tax_compliance"]},
            {"id": "voter_card", "name": "Voter Registration Card", "required": False, "fields": ["document_number", "full_name", "polling_station", "constituency", "county"]},
            {"id": "driving_license", "name": "Driving License", "required": False, "fields": ["document_number", "issue_date", "expiry_date", "full_name", "license_class", "blood_group"]}
        ]
    },
    "employment": {
        "name": "EMPLOYMENT & SOCIAL SECURITY",
        "icon": "💼",
        "order": 4,
        "documents": [
            {"id": "employment_contract", "name": "Employment Contract", "required": False, "fields": ["employer_name", "issue_date", "full_name", "job_title", "employment_type", "start_date", "end_date"]},
            {"id": "nhif_card", "name": "NHIF Card", "required": True, "fields": ["nhif_number", "issue_date", "full_name", "employer_name", "contribution_status"]},
            {"id": "nssf_card", "name": "NSSF Card", "required": True, "fields": ["nssf_number", "issue_date", "full_name", "employer_name", "contribution_status"]},
            {"id": "professional_cert", "name": "Professional Certificate", "required": False, "fields": ["document_number", "issue_date", "full_name", "institution", "qualification", "registration_number"]},
            {"id": "payslip", "name": "Payslip", "required": False, "fields": ["employer_name", "full_name", "month", "basic_salary", "net_pay"]}
        ]
    },
    "business_property": {
        "name": "BUSINESS, PROPERTY & FINANCE",
        "icon": "🏦",
        "order": 5,
        "documents": [
            {"id": "title_deed", "name": "Title Deed", "required": False, "fields": ["document_number", "issue_date", "full_name", "property_location", "land_reference", "size_acres"]},
            {"id": "business_permit", "name": "Business Permit", "required": False, "fields": ["document_number", "issue_date", "expiry_date", "business_name", "business_type", "location"]},
            {"id": "lease_agreement", "name": "Lease Agreement", "required": False, "fields": ["document_number", "issue_date", "full_name", "landlord_name", "property_address", "rent_amount", "lease_term"]},
            {"id": "loan_agreement", "name": "Loan Agreement", "required": False, "fields": ["document_number", "issue_date", "full_name", "bank_name", "loan_amount", "interest_rate", "repayment_period"]},
            {"id": "cr12", "name": "CR12 Certificate of Incorporation", "required": False, "fields": ["document_number", "issue_date", "company_name", "registration_number", "directors"]},
            {"id": "tax_compliance", "name": "Tax Compliance Certificate", "required": False, "fields": ["document_number", "issue_date", "expiry_date", "company_name", "kra_pin", "compliance_status"]}
        ]
    },
    "transport": {
        "name": "TRANSPORT & ASSETS",
        "icon": "🚗",
        "order": 6,
        "documents": [
            {"id": "vehicle_logbook", "name": "Vehicle Logbook", "required": False, "fields": ["document_number", "issue_date", "vehicle_registration", "full_name", "make_model", "year_manufacture", "engine_number", "chassis_number"]},
            {"id": "insurance_cert", "name": "Insurance Certificate", "required": False, "fields": ["document_number", "issue_date", "expiry_date", "vehicle_registration", "insurance_company", "policy_type", "cover_amount"]},
            {"id": "road_service_license", "name": "Road Service License", "required": False, "fields": ["document_number", "issue_date", "expiry_date", "vehicle_registration", "route"]},
            {"id": "vehicle_transfer", "name": "Vehicle Transfer Documents", "required": False, "fields": ["document_number", "issue_date", "vehicle_registration", "seller_name", "buyer_name", "transfer_date"]}
        ]
    },
    "family": {
        "name": "FAMILY & PERSONAL STATUS",
        "icon": "💒",
        "order": 7,
        "documents": [
            {"id": "marriage_cert", "name": "Marriage Certificate", "required": False, "fields": ["document_number", "marriage_date", "full_name", "spouse_name", "marriage_place", "marriage_type", "witnesses"]},
            {"id": "divorce_decree", "name": "Divorce Decree", "required": False, "fields": ["document_number", "issue_date", "full_name", "ex_spouse_name", "divorce_date", "court_name", "court_case_number"]},
            {"id": "child_birth_cert", "name": "Child's Birth Certificate", "required": False, "fields": ["document_number", "issue_date", "full_name", "date_of_birth", "child_name", "gender"]},
            {"id": "adoption_cert", "name": "Adoption Certificate", "required": False, "fields": ["document_number", "issue_date", "full_name", "child_name", "adoption_date", "court_order_number"]}
        ]
    },
    "legal": {
        "name": "LEGAL & COURT DOCUMENTS",
        "icon": "⚖️",
        "order": 8,
        "documents": [
            {"id": "police_clearance", "name": "Police Clearance Certificate", "required": False, "fields": ["document_number", "issue_date", "full_name", "id_number", "purpose", "valid_until"]},
            {"id": "court_order", "name": "Court Order", "required": False, "fields": ["document_number", "issue_date", "full_name", "court_name", "court_case_number", "order_type", "judge_name"]},
            {"id": "affidavit", "name": "Affidavit", "required": False, "fields": ["document_number", "issue_date", "full_name", "commissioner_name", "deposition_date", "case_number"]},
            {"id": "succession_cert", "name": "Succession Certificate", "required": False, "fields": ["document_number", "issue_date", "full_name", "deceased_name", "court_name", "grant_letter"]}
        ]
    },
    "retirement": {
        "name": "RETIREMENT & ESTATE",
        "icon": "👴",
        "order": 9,
        "documents": [
            {"id": "pension_docs", "name": "Pension Documents", "required": False, "fields": ["document_number", "issue_date", "full_name", "employer_name", "pension_scheme", "retirement_date", "monthly_pension"]},
            {"id": "will", "name": "Last Will & Testament", "required": False, "fields": ["document_number", "execution_date", "full_name", "executor_name", "witnesses", "beneficiaries"]},
            {"id": "retirement_benefits", "name": "Retirement Benefits Statement", "required": False, "fields": ["document_number", "statement_date", "full_name", "employer_name", "total_benefits", "lump_sum", "annuity"]}
        ]
    }
}

# ==================== FIELD CONFIGURATIONS ====================
field_configs = {
    'document_number': {'label': 'Document Number', 'type': 'text', 'placeholder': 'Enter document number', 'required': True},
    'issue_date': {'label': 'Issue Date', 'type': 'date', 'placeholder': '', 'required': True},
    'expiry_date': {'label': 'Expiry Date', 'type': 'date', 'placeholder': '', 'required': False},
    'full_name': {'label': 'Full Name', 'type': 'text', 'placeholder': 'Enter full name as on document', 'required': True},
    'date_of_birth': {'label': 'Date of Birth', 'type': 'date', 'placeholder': '', 'required': True},
    'place_of_birth': {'label': 'Place of Birth', 'type': 'text', 'placeholder': 'City, County', 'required': False},
    'mother_name': {'label': "Mother's Name", 'type': 'text', 'placeholder': "Enter mother's full name", 'required': False},
    'father_name': {'label': "Father's Name", 'type': 'text', 'placeholder': "Enter father's full name", 'required': False},
    'hospital_name': {'label': 'Hospital/Facility Name', 'type': 'text', 'placeholder': 'Enter hospital name', 'required': False},
    'school_name': {'label': 'School/Institution Name', 'type': 'text', 'placeholder': 'Enter school name', 'required': True},
    'candidate_index': {'label': 'Candidate Index Number', 'type': 'text', 'placeholder': 'Enter index number', 'required': True},
    'total_marks': {'label': 'Total Marks', 'type': 'number', 'placeholder': 'e.g., 482', 'required': False},
    'mean_grade': {'label': 'Mean Grade', 'type': 'text', 'placeholder': 'e.g., A-, B+', 'required': True},
    'class_name': {'label': 'Class/Form', 'type': 'text', 'placeholder': 'e.g., Class 8, Form 4', 'required': False},
    'academic_year': {'label': 'Academic Year', 'type': 'text', 'placeholder': 'e.g., 2023', 'required': False},
    'id_serial_number': {'label': 'ID Serial Number', 'type': 'text', 'placeholder': 'Serial number on back of ID', 'required': False},
    'place_of_issue': {'label': 'Place of Issue', 'type': 'text', 'placeholder': 'Where document was issued', 'required': False},
    'passport_type': {'label': 'Passport Type', 'type': 'select', 'options': ['Ordinary', 'Diplomatic', 'Official', 'East African'], 'required': False},
    'country_of_issue': {'label': 'Country of Issue', 'type': 'text', 'placeholder': 'Country', 'required': False},
    'kra_pin': {'label': 'KRA PIN Number', 'type': 'text', 'placeholder': 'Enter KRA PIN (A001234567X)', 'required': True},
    'pin_status': {'label': 'PIN Status', 'type': 'select', 'options': ['Active', 'Inactive', 'Suspended'], 'required': False},
    'tax_compliance': {'label': 'Tax Compliance Status', 'type': 'select', 'options': ['Compliant', 'Non-Compliant', 'Pending'], 'required': False},
    'polling_station': {'label': 'Polling Station', 'type': 'text', 'placeholder': 'Enter polling station name', 'required': False},
    'constituency': {'label': 'Constituency', 'type': 'text', 'placeholder': 'Enter constituency', 'required': False},
    'county': {'label': 'County', 'type': 'text', 'placeholder': 'Enter county', 'required': False},
    'license_class': {'label': 'License Class', 'type': 'text', 'placeholder': 'e.g., B, C, E', 'required': False},
    'blood_group': {'label': 'Blood Group', 'type': 'select', 'options': ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'], 'required': False},
    'employer_name': {'label': 'Employer Name', 'type': 'text', 'placeholder': 'Enter employer/business name', 'required': True},
    'job_title': {'label': 'Job Title', 'type': 'text', 'placeholder': 'e.g., Accountant, Manager', 'required': False},
    'employment_type': {'label': 'Employment Type', 'type': 'select', 'options': ['Permanent', 'Contract', 'Part-time', 'Casual', 'Internship'], 'required': False},
    'start_date': {'label': 'Start Date', 'type': 'date', 'placeholder': '', 'required': False},
    'end_date': {'label': 'End Date', 'type': 'date', 'placeholder': '', 'required': False},
    'nhif_number': {'label': 'NHIF Number', 'type': 'text', 'placeholder': 'Enter NHIF number', 'required': True},
    'nssf_number': {'label': 'NSSF Number', 'type': 'text', 'placeholder': 'Enter NSSF number', 'required': True},
    'contribution_status': {'label': 'Contribution Status', 'type': 'select', 'options': ['Active', 'Inactive', 'Defaulting'], 'required': False},
    'institution': {'label': 'Institution', 'type': 'text', 'placeholder': 'e.g., KASNEB, University', 'required': False},
    'qualification': {'label': 'Qualification', 'type': 'text', 'placeholder': 'e.g., CPA, Bachelor Degree', 'required': False},
    'registration_number': {'label': 'Registration Number', 'type': 'text', 'placeholder': 'Professional registration number', 'required': False},
    'month': {'label': 'Month/Year', 'type': 'month', 'placeholder': '', 'required': False},
    'basic_salary': {'label': 'Basic Salary (KES)', 'type': 'number', 'placeholder': 'Enter amount', 'required': False},
    'net_pay': {'label': 'Net Pay (KES)', 'type': 'number', 'placeholder': 'Enter amount', 'required': False},
    'property_location': {'label': 'Property Location', 'type': 'text', 'placeholder': 'County/Town/Area', 'required': True},
    'land_reference': {'label': 'Land Reference Number', 'type': 'text', 'placeholder': 'e.g., LR No. 12345', 'required': True},
    'size_acres': {'label': 'Size (Acres)', 'type': 'text', 'placeholder': 'e.g., 0.5 acres', 'required': False},
    'business_name': {'label': 'Business Name', 'type': 'text', 'placeholder': 'Registered business name', 'required': True},
    'business_type': {'label': 'Business Type', 'type': 'text', 'placeholder': 'e.g., Retail, Services', 'required': False},
    'location': {'label': 'Business Location', 'type': 'text', 'placeholder': 'Physical address', 'required': False},
    'landlord_name': {'label': "Landlord's Name", 'type': 'text', 'placeholder': 'Full name of landlord', 'required': False},
    'property_address': {'label': 'Property Address', 'type': 'text', 'placeholder': 'Full property address', 'required': True},
    'rent_amount': {'label': 'Monthly Rent (KES)', 'type': 'number', 'placeholder': 'Enter amount', 'required': True},
    'lease_term': {'label': 'Lease Term', 'type': 'text', 'placeholder': 'e.g., 12 months', 'required': False},
    'bank_name': {'label': 'Bank Name', 'type': 'text', 'placeholder': 'Name of bank', 'required': True},
    'loan_amount': {'label': 'Loan Amount (KES)', 'type': 'number', 'placeholder': 'Enter amount', 'required': True},
    'interest_rate': {'label': 'Interest Rate (%)', 'type': 'number', 'placeholder': 'e.g., 13.5', 'required': False},
    'repayment_period': {'label': 'Repayment Period', 'type': 'text', 'placeholder': 'e.g., 60 months', 'required': False},
    'company_name': {'label': 'Company Name', 'type': 'text', 'placeholder': 'Registered company name', 'required': True},
    'directors': {'label': 'Directors', 'type': 'text', 'placeholder': 'Names of directors', 'required': False},
    'vehicle_registration': {'label': 'Vehicle Registration Number', 'type': 'text', 'placeholder': 'e.g., KCA 123A', 'required': True},
    'make_model': {'label': 'Make & Model', 'type': 'text', 'placeholder': 'e.g., Toyota Probox', 'required': True},
    'year_manufacture': {'label': 'Year of Manufacture', 'type': 'number', 'placeholder': 'e.g., 2020', 'required': False},
    'engine_number': {'label': 'Engine Number', 'type': 'text', 'placeholder': 'Engine identification number', 'required': False},
    'chassis_number': {'label': 'Chassis Number', 'type': 'text', 'placeholder': 'Chassis identification number', 'required': False},
    'insurance_company': {'label': 'Insurance Company', 'type': 'text', 'placeholder': 'Name of insurer', 'required': True},
    'policy_type': {'label': 'Policy Type', 'type': 'select', 'options': ['Comprehensive', 'Third Party', 'Third Party Fire & Theft'], 'required': True},
    'cover_amount': {'label': 'Cover Amount (KES)', 'type': 'number', 'placeholder': 'Enter amount', 'required': False},
    'route': {'label': 'Route/Licensed Area', 'type': 'text', 'placeholder': 'e.g., Nairobi - Mombasa', 'required': False},
    'seller_name': {'label': "Seller's Name", 'type': 'text', 'placeholder': 'Previous owner name', 'required': True},
    'buyer_name': {'label': "Buyer's Name", 'type': 'text', 'placeholder': 'New owner name', 'required': True},
    'transfer_date': {'label': 'Transfer Date', 'type': 'date', 'placeholder': '', 'required': True},
    'spouse_name': {'label': "Spouse's Name", 'type': 'text', 'placeholder': 'Full name of spouse', 'required': True},
    'marriage_place': {'label': 'Place of Marriage', 'type': 'text', 'placeholder': 'Church, Court, etc.', 'required': True},
    'marriage_type': {'label': 'Marriage Type', 'type': 'select', 'options': ['Civil', 'Christian', 'Muslim', 'Hindu', 'African Customary'], 'required': True},
    'witnesses': {'label': 'Witnesses', 'type': 'text', 'placeholder': 'Names of witnesses', 'required': False},
    'ex_spouse_name': {'label': "Ex-Spouse's Name", 'type': 'text', 'placeholder': 'Name of ex-spouse', 'required': True},
    'divorce_date': {'label': 'Divorce Date', 'type': 'date', 'placeholder': '', 'required': True},
    'child_name': {'label': "Child's Name", 'type': 'text', 'placeholder': 'Full name of child', 'required': True},
    'gender': {'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female'], 'required': True},
    'adoption_date': {'label': 'Adoption Date', 'type': 'date', 'placeholder': '', 'required': True},
    'court_order_number': {'label': 'Court Order Number', 'type': 'text', 'placeholder': 'Court order number', 'required': True},
    'purpose': {'label': 'Purpose of Clearance', 'type': 'text', 'placeholder': 'e.g., Employment, Travel', 'required': False},
    'valid_until': {'label': 'Valid Until', 'type': 'date', 'placeholder': '', 'required': False},
    'court_name': {'label': 'Court Name', 'type': 'text', 'placeholder': 'e.g., Milimani Law Courts', 'required': True},
    'court_case_number': {'label': 'Court Case Number', 'type': 'text', 'placeholder': 'Case reference number', 'required': True},
    'order_type': {'label': 'Order Type', 'type': 'text', 'placeholder': 'e.g., Injunction, Judgment', 'required': False},
    'judge_name': {'label': "Judge's Name", 'type': 'text', 'placeholder': 'Name of presiding judge', 'required': False},
    'commissioner_name': {'label': "Commissioner's Name", 'type': 'text', 'placeholder': 'Name of commissioner of oaths', 'required': True},
    'deposition_date': {'label': 'Deposition Date', 'type': 'date', 'placeholder': '', 'required': True},
    'case_number': {'label': 'Case Number', 'type': 'text', 'placeholder': 'Associated case number', 'required': True},
    'deceased_name': {'label': "Deceased's Name", 'type': 'text', 'placeholder': 'Name of deceased', 'required': True},
    'grant_letter': {'label': 'Grant Letter Reference', 'type': 'text', 'placeholder': 'Grant letter number', 'required': False},
    'pension_scheme': {'label': 'Pension Scheme Name', 'type': 'text', 'placeholder': 'Name of pension scheme', 'required': True},
    'retirement_date': {'label': 'Retirement Date', 'type': 'date', 'placeholder': '', 'required': True},
    'monthly_pension': {'label': 'Monthly Pension (KES)', 'type': 'number', 'placeholder': 'Enter amount', 'required': True},
    'execution_date': {'label': 'Will Execution Date', 'type': 'date', 'placeholder': '', 'required': True},
    'executor_name': {'label': "Executor's Name", 'type': 'text', 'placeholder': 'Name of executor', 'required': True},
    'beneficiaries': {'label': 'Beneficiaries', 'type': 'text', 'placeholder': 'List of beneficiaries', 'required': False},
    'statement_date': {'label': 'Statement Date', 'type': 'date', 'placeholder': '', 'required': True},
    'total_benefits': {'label': 'Total Benefits (KES)', 'type': 'number', 'placeholder': 'Enter total amount', 'required': True},
    'lump_sum': {'label': 'Lump Sum Amount (KES)', 'type': 'number', 'placeholder': 'Enter lump sum', 'required': False},
    'annuity': {'label': 'Monthly Annuity (KES)', 'type': 'number', 'placeholder': 'Enter monthly amount', 'required': False}
}

# ==================== HELPER FUNCTIONS ====================
def save_user_to_database(user_id, email, full_name, avatar_url=None):
    try:
        existing = supabase.table("users").select("*").eq("id", user_id).execute()
        if not existing.data:
            user_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "is_active": True,
                "terms_accepted": True
            }
            supabase.table("users").insert(user_data).execute()
            print(f"✅ New user {email} saved")
        else:
            supabase.table("users").update({
                "last_login": datetime.now().isoformat()
            }).eq("id", user_id).execute()
            print(f"✅ User {email} last login updated")
    except Exception as e:
        print(f"❌ Error saving user: {e}")

# ==================== CHECK USER EXISTS ====================
@app.route("/check_user_exists", methods=["POST"])
def check_user_exists():
    try:
        data = request.get_json()
        email = data.get("email")
        if not email:
            return jsonify({"exists": False, "error": "Email required"}), 400
        user_response = supabase.table("users").select("id").eq("email", email).execute()
        return jsonify({"exists": len(user_response.data) > 0})
    except Exception as e:
        print(f"Check user error: {e}")
        return jsonify({"exists": False}), 500

# ==================== REGISTRATION ====================
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        terms_accepted = data.get("terms_accepted", False)
        
        if not email or not password or not full_name:
            return jsonify({"success": False, "error": "All fields are required"}), 400
        if not terms_accepted:
            return jsonify({"success": False, "error": "You must accept the Terms of Service"}), 400
        
        existing_user = supabase.table("users").select("id").eq("email", email).execute()
        if existing_user.data:
            return jsonify({"success": False, "error": "Email already registered. Please login."}), 400
        
        user = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name, "email": email}}
        })
        
        user_id = None
        if hasattr(user, 'user') and user.user:
            user_id = user.user.id
        elif hasattr(user, 'id'):
            user_id = user.id
        
        if user_id:
            save_user_to_database(user_id, email, full_name)
            session["logged_in"] = True
            session["user_id"] = user_id
            session["user_email"] = email
            session["user_name"] = full_name.split()[0] if full_name else email.split('@')[0]
            session["user_avatar"] = ""
            session["terms_accepted"] = True
            return jsonify({"success": True, "redirect": "/dashboard"})
        return jsonify({"success": False, "error": "Registration failed"}), 400
    except Exception as e:
        print(f"Registration error: {e}")
        error_msg = str(e)
        if "User already registered" in error_msg:
            return jsonify({"success": False, "error": "Email already registered. Please login."}), 400
        return jsonify({"success": False, "error": error_msg}), 500

# ==================== EMAIL LOGIN ====================
@app.route("/login_email", methods=["POST"])
def login_email():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        user_check = supabase.table("users").select("id").eq("email", email).execute()
        if not user_check.data:
            return jsonify({"success": False, "error": "No account found. Please register first."}), 404
        
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if user and user.user:
            user_id = user.user.id
            user_email = user.user.email
            full_name = user.user.user_metadata.get("full_name", user_email.split('@')[0])
            save_user_to_database(user_id, user_email, full_name)
            
            session["logged_in"] = True
            session["user_id"] = user_id
            session["user_email"] = user_email
            session["user_name"] = full_name.split()[0]
            session["user_avatar"] = ""
            session["terms_accepted"] = True
            return jsonify({"success": True, "redirect": "/dashboard"})
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

# ==================== GOOGLE OAUTH ====================
@app.route("/auth/google")
def auth_google():
    try:
        redirect_url = "http://localhost:5000/callback"
        
        auth_response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "scopes": "email profile",
                "redirect_to": redirect_url
            }
        })
        
        if hasattr(auth_response, 'url'):
            return redirect(auth_response.url)
        elif isinstance(auth_response, dict) and 'url' in auth_response:
            return redirect(auth_response['url'])
        return "Authentication failed", 500
    except Exception as e:
        print(f"Google Auth error: {e}")
        return redirect(url_for('home'))

# ==================== CALLBACK ROUTE - FIXED VERSION ====================
@app.route("/callback")
def callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            print("No code received in callback")
            return redirect(url_for('home'))
        
        print(f"📍 Received auth code: {code[:50]}...")
        
        # METHOD 1: Try exchange_code_for_session with dictionary
        try:
            session_data = supabase.auth.exchange_code_for_session({
                "auth_code": code
            })
            print("✅ Method 1 succeeded")
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
            # METHOD 2: Try direct REST API call
            try:
                token_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=authorization_code"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "code": code
                }
                response = requests.post(token_url, headers=headers, json=payload)
                if response.status_code == 200:
                    session_data = response.json()
                    print("✅ Method 2 (REST API) succeeded")
                else:
                    print(f"REST API error: {response.status_code} - {response.text}")
                    return redirect(url_for('home'))
            except Exception as e2:
                print(f"Method 2 failed: {e2}")
                return redirect(url_for('home'))
        
        # Extract user from session_data
        user = None
        if hasattr(session_data, 'user'):
            user = session_data.user
        elif isinstance(session_data, dict) and 'user' in session_data:
            user = session_data['user']
        
        if user:
            # Extract user info
            user_id = user.id if hasattr(user, 'id') else user.get('id')
            user_email = user.email if hasattr(user, 'email') else user.get('email')
            
            user_metadata = {}
            if hasattr(user, 'user_metadata'):
                user_metadata = user.user_metadata
            elif isinstance(user, dict) and 'user_metadata' in user:
                user_metadata = user['user_metadata']
            
            full_name = user_metadata.get('full_name', user_metadata.get('name', user_email.split('@')[0] if user_email else 'User'))
            avatar_url = user_metadata.get('avatar_url', user_metadata.get('picture', ''))
            
            print(f"👤 User authenticated: {user_email} ({full_name})")
            
            # Save to database
            save_user_to_database(user_id, user_email, full_name, avatar_url)
            
            # Set session
            session["logged_in"] = True
            session["user_id"] = user_id
            session["user_email"] = user_email
            session["user_name"] = full_name.split()[0] if ' ' in full_name else full_name
            session["user_avatar"] = avatar_url
            session["terms_accepted"] = True
            
            print(f"✅ Redirecting to dashboard...")
            return redirect(url_for('dashboard'))
        else:
            print("❌ No user data in session response")
            return redirect(url_for('home'))
            
    except Exception as e:
        print(f"❌ Callback error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('home'))

# ==================== MAIN ROUTES ====================
@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect(url_for('dashboard'))
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for('home'))
    user_info = {
        "email": session.get("user_email"),
        "name": session.get("user_name"),
        "avatar": session.get("user_avatar", ""),
        "user_id": session.get("user_id"),
        "terms_accepted": session.get("terms_accepted", True)
    }
    return render_template("dashboard.html", user=user_info, categories=DOCUMENT_CATEGORIES)

@app.route("/logout")
def logout():
    try:
        supabase.auth.sign_out()
    except:
        pass
    session.clear()
    return redirect(url_for('home'))

# ==================== PAGE ROUTES ====================
@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/categories")
def categories():
    return render_template("categories.html", categories=DOCUMENT_CATEGORIES)

@app.route("/about")
def about():
    return render_template("about.html")

# ==================== DOCUMENT API ROUTES ====================
@app.route("/api/document_fields/<category_id>/<document_id>")
def get_document_fields(category_id, document_id):
    category = DOCUMENT_CATEGORIES.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404
    document = next((d for d in category["documents"] if d["id"] == document_id), None)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    fields_data = []
    for field in document.get("fields", []):
        if field in field_configs:
            fields_data.append(field_configs[field])
    return jsonify({
        "document_name": document["name"],
        "fields": fields_data,
        "required": document.get("required", False)
    })

@app.route("/save_document", methods=["POST"])
def save_document():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.form.to_dict()
        front_image = request.files.get('front_image')
        back_image = request.files.get('back_image')
        
        front_image_url = None
        back_image_url = None
        
        if front_image and front_image.filename:
            front_image_url = f"data:{front_image.content_type};base64,{base64.b64encode(front_image.read()).decode('utf-8')}"
        if back_image and back_image.filename:
            back_image_url = f"data:{back_image.content_type};base64,{base64.b64encode(back_image.read()).decode('utf-8')}"
        
        document_data = {
            "user_id": session.get("user_id"),
            "user_email": session.get("user_email"),
            "category_id": data.get("category_id"),
            "document_id": data.get("document_id"),
            "document_name": data.get("document_name"),
            "status": data.get("status", "pending"),
            "notes": data.get("notes", ""),
            "front_image_url": front_image_url,
            "back_image_url": back_image_url,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        field_mapping = {
            "mother's_name": "mother_name",
            "father's_name": "father_name",
            "spouse's_name": "spouse_name",
            "child's_name": "child_name",
            "seller's_name": "seller_name",
            "buyer's_name": "buyer_name",
            "ex-spouse_name": "ex_spouse_name",
            "deceased's_name": "deceased_name",
            "landlord's_name": "landlord_name",
            "executor's_name": "executor_name",
            "commissioner's_name": "commissioner_name",
            "judge's_name": "judge_name",
            "date of birth": "date_of_birth",
            "place of birth": "place_of_birth",
            "full name": "full_name",
        }
        
        for key, value in data.items():
            if value and key not in ['category_id', 'document_id', 'document_name', 'status', 'notes']:
                if key in field_mapping:
                    db_key = field_mapping[key]
                else:
                    db_key = key.replace(" ", "_").replace("'", "").replace("-", "_").lower()
                document_data[db_key] = value
        
        result = supabase.table("user_documents").insert(document_data).execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        print(f"Save error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/documents/<int:doc_id>", methods=["PUT"])
def update_document(doc_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        if request.content_type and 'multipart' in request.content_type:
            data = request.form.to_dict()
            front_image = request.files.get('front_image')
            back_image = request.files.get('back_image')
            if front_image and front_image.filename:
                data['front_image_url'] = f"data:{front_image.content_type};base64,{base64.b64encode(front_image.read()).decode('utf-8')}"
            if back_image and back_image.filename:
                data['back_image_url'] = f"data:{back_image.content_type};base64,{base64.b64encode(back_image.read()).decode('utf-8')}"
        else:
            data = request.get_json()
        
        data['updated_at'] = datetime.now().isoformat()
        
        field_mapping = {
            "mother's_name": "mother_name",
            "father's_name": "father_name",
            "spouse's_name": "spouse_name",
            "child's_name": "child_name",
            "seller's_name": "seller_name",
            "buyer's_name": "buyer_name",
            "ex-spouse_name": "ex_spouse_name",
            "deceased's_name": "deceased_name",
            "landlord's_name": "landlord_name",
            "executor's_name": "executor_name",
            "commissioner's_name": "commissioner_name",
            "judge's_name": "judge_name",
            "date of birth": "date_of_birth",
            "place of birth": "place_of_birth",
            "full name": "full_name",
        }
        
        update_data = {}
        for k, v in data.items():
            if v is not None and k not in ['front_image', 'back_image']:
                if k in field_mapping:
                    db_key = field_mapping[k]
                else:
                    db_key = k.replace(" ", "_").replace("'", "").replace("-", "_").lower()
                update_data[db_key] = v
        
        supabase.table("user_documents").update(update_data).eq("id", doc_id).eq("user_id", session.get("user_id")).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Update error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/documents")
def get_documents():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        response = supabase.table("user_documents").select("*").eq("user_id", session.get("user_id")).order("created_at", desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        print(f"Fetch error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/document/<int:doc_id>")
def get_document(doc_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        response = supabase.table("user_documents").select("*").eq("id", doc_id).eq("user_id", session.get("user_id")).execute()
        if response.data:
            return jsonify(response.data[0])
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        supabase.table("user_documents").delete().eq("id", doc_id).eq("user_id", session.get("user_id")).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/document_receipt/<int:doc_id>")
def document_receipt(doc_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        response = supabase.table("user_documents").select("*").eq("id", doc_id).eq("user_id", session.get("user_id")).execute()
        if not response.data:
            return jsonify({"error": "Not found"}), 404
        doc = response.data[0]
        qr_data = f"Document: {doc.get('document_name')}\nOwner: {doc.get('user_email')}\nID: {doc_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        buffered = BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(buffered, format="PNG")
        return jsonify({
            "success": True,
            "document": doc,
            "qr_code": f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/verify/<int:doc_id>")
def verify_document(doc_id):
    try:
        response = supabase.table("user_documents").select("*").eq("id", doc_id).execute()
        if response.data:
            doc = response.data[0]
            return f"""
            <html>
            <head><title>Verified Document</title><script src="https://cdn.tailwindcss.com"></script></head>
            <body class="bg-gray-100">
                <div class="max-w-2xl mx-auto mt-20 p-8 bg-white rounded-xl shadow-lg">
                    <div class="text-center"><div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4"><svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
                    <h1 class="text-2xl font-bold">Verified Document</h1>
                    <p>Document: {doc.get('document_name')}</p>
                    <p>Owner: {doc.get('user_email')}</p>
                    <p>Status: {doc.get('status')}</p>
                    <p>Verified: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></div>
                </div>
            </body>
            </html>
            """
        return "Not found", 404
    except Exception as e:
        return f"Error: {e}", 500

@app.context_processor
def utility_processor():
    return dict(now=datetime.now, current_year=datetime.now().year)
@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        full_name = data.get("full_name")
        phone = data.get("phone")
        
        update_data = {
            "full_name": full_name,
            "phone": phone,
            "updated_at": datetime.now().isoformat()
        }
        
        supabase.table("users").update(update_data).eq("id", session.get("user_id")).execute()
        
        session["user_name"] = full_name.split()[0] if full_name else session.get("user_name")
        
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        print(f"Profile update error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
if __name__ == "__main__":
    
    app.run(debug=True, host='localhost', port=5000)