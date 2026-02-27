import anvil.server
import anvil.users
import json
import anvil.media
import mysql.connector
from dotenv import load_dotenv
import os
from contextlib import contextmanager
import re
import pdfkit
import decimal
import base64

# Set your wkhtmltopdf path here (adjust for your system)
WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"  # Windows path
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

# Load environment variables from .env file
load_dotenv()

# Connect to Anvil server
anvil.server.connect("server_TA5BI466VDEZYA3VQB6RJ2L7-FH6BWWYXOCTYHXHG")

# Function to establish DB connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "3306"),
        database=os.getenv("DB_NAME"),
        auth_plugin=os.getenv("DB_AUTH_PLUGIN", "mysql_native_password"),
    )


# Context manager for DB cursor
@contextmanager
def db_cursor():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        cursor.close()
        connection.close()


# *************************************************** BMA Messenger Application - Verify Login Credentials ************************************
@anvil.server.callable()
def test():
    return "Hello from Anvil server!"

@anvil.server.http_endpoint("/verify-login", methods=["POST"])
def verify_login(email=None, password=None):
    try:
        if not email or not password:
            return anvil.server.HttpResponse(
                400,
                json.dumps({"success": False, "error": "Email and password are required"}),
                headers={"Content-Type": "application/json"}
            )

        # Attempt login using Anvil's built-in user authentication
        try:
            user = anvil.users.login_with_email(email, password)
        except anvil.users.AuthenticationFailed:
            return anvil.server.HttpResponse(
                401,
                json.dumps({"success": False, "error": "Invalid email or password"}),
                headers={"Content-Type": "application/json"}
            )

        if user is None:
            return anvil.server.HttpResponse(
                401,
                json.dumps({"success": False, "error": "Invalid email or password"}),
                headers={"Content-Type": "application/json"}
            )

        user_data = {
            "email":  user["email"],
            "roleId": str(user.get("role_id", ""))
        }

        return anvil.server.HttpResponse(
            200,
            json.dumps({"success": True, "user": user_data}),
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        print(f"Login error: {str(e)}")
        return anvil.server.HttpResponse(
            500,
            json.dumps({"success": False, "error": f"Internal Server Error: {str(e)}"}),
            headers={"Content-Type": "application/json"}
        )
# *************************************************** BMA Messenger Application - PDF Generation Section ************************************************

@anvil.server.callable()
def getQuotationInvoiceName(jobCardID):
    with db_cursor() as cursor:
        query = """
            SELECT JobCardRef
            FROM tbl_jobcarddetails
            WHERE ID = %s
        """

        cursor.execute(query, (jobCardID,))
        result = cursor.fetchone()
        return result[0]

@anvil.server.callable()
def get_quote_details_by_job_id(job_id):
    with db_cursor() as cursor:
        query = """
        SELECT
            tbl_clientcontacts.Fullname,
            tbl_jobcarddetails.MakeAndModel,
            tbl_jobcarddetails.RegNo,
            tbl_quotation.Date,
            tbl_jobcarddetails.ChassisNo,
            tbl_jobcarddetails.EngineCode,
            tbl_jobcarddetails.Mileage,
            tbl_quotation.Item,
            tbl_quotation.QuantityIssued,
            tbl_quotation.Amount,
            tbl_quotation.AssignedJobID
        FROM
            (tbl_jobcarddetails
            INNER JOIN tbl_clientcontacts
            ON tbl_jobcarddetails.ClientDetails = tbl_clientcontacts.ID)
        INNER JOIN tbl_quotation
            ON tbl_jobcarddetails.ID = tbl_quotation.AssignedJobID
        WHERE tbl_quotation.AssignedJobID = %s
        """
        cursor.execute(query, (job_id,))
        rows = cursor.fetchall()

        result = []
        for r in rows:
            # Helper function to ensure we get a float from various types
            def safe_float_convert(value):
                if value is None:
                    return None  # Or 0.0, depending on desired behavior for NULLs
                if isinstance(value, (int, float, decimal.Decimal)):
                    return float(value)
                # If it's a string, try to clean it and convert
                if isinstance(value, str):
                    try:
                        return float(value.replace(",", ""))
                    except ValueError:
                        # Handle cases where string cannot be converted (e.g., non-numeric string)
                        print(f"Warning: Could not convert string '{value}' to float.")
                        return None  # Or raise an error
                return None  # Default if type is unexpected

            quantity_issued_val = safe_float_convert(r[8])  # QuantityIssued
            amount_val = safe_float_convert(r[9])  # Amount

            # Ensure 'QuantityIssued' for the dictionary can be "" if originally None or non-numeric string
            # If your front-end expects an empty string, keep this logic
            display_quantity_issued = (
                ""
                if r[8] is None or not isinstance(r[8], (int, float, decimal.Decimal))
                else quantity_issued_val
            )

            # Calculate Total - ensuring we use the float versions for calculation
            total_calc = None
            if quantity_issued_val is None:  # If QuantityIssued was NULL/None from DB
                total_calc = amount_val
            elif amount_val is not None:  # Ensure Amount is not None for multiplication
                total_calc = round(quantity_issued_val * amount_val, 2)
            # If amount_val is None and quantity_issued_val is not None, total_calc would remain None

            result.append(
                {
                    "Fullname": r[0],
                    "MakeAndModel": r[1],
                    "RegNo": r[2],
                    "Date": r[3],
                    "ChassisNo": r[4],
                    "EngineCode": r[5],
                    "Mileage": r[6],
                    "Item": r[7],
                    "QuantityIssued": display_quantity_issued,  # Use the potentially "" value for display
                    "Amount": amount_val,  # This is now always a float or None
                    "AssignedJobID": r[10],
                    "Total": total_calc,  # This is now always a float or None
                }
            )

        return result


@anvil.server.callable()
def get_quote_confirmation_details_by_job_id(job_id):
    with db_cursor() as cursor:
        query = """
        SELECT
            tbl_clientcontacts.Fullname,
            tbl_jobcarddetails.MakeAndModel,
            tbl_jobcarddetails.RegNo,
            tbl_quotationpartsandservicesfeedback.Date,
            tbl_jobcarddetails.ChassisNo,
            tbl_jobcarddetails.EngineCode,
            tbl_jobcarddetails.Mileage,
            tbl_quotationpartsandservicesfeedback.Item,
            tbl_quotationpartsandservicesfeedback.QuantityIssued,
            tbl_quotationpartsandservicesfeedback.Amount,
            tbl_quotationpartsandservicesfeedback.AssignedJobID
        FROM
            (tbl_jobcarddetails
            INNER JOIN tbl_clientcontacts
            ON tbl_jobcarddetails.ClientDetails = tbl_clientcontacts.ID)
        INNER JOIN tbl_quotationpartsandservicesfeedback
            ON tbl_jobcarddetails.ID = tbl_quotationpartsandservicesfeedback.AssignedJobID
        WHERE tbl_quotationpartsandservicesfeedback.AssignedJobID = %s
        """
        cursor.execute(query, (job_id,))
        rows = cursor.fetchall()

        result = []
        for r in rows:
            # Helper function to ensure we get a float from various types
            def safe_float_convert(value):
                if value is None:
                    return None  # Or 0.0, depending on desired behavior for NULLs
                if isinstance(value, (int, float, decimal.Decimal)):
                    return float(value)
                # If it's a string, try to clean it and convert
                if isinstance(value, str):
                    try:
                        return float(value.replace(",", ""))
                    except ValueError:
                        # Handle cases where string cannot be converted (e.g., non-numeric string)
                        print(f"Warning: Could not convert string '{value}' to float.")
                        return None  # Or raise an error
                return None  # Default if type is unexpected

            quantity_issued_val = safe_float_convert(r[8])  # QuantityIssued
            amount_val = safe_float_convert(r[9])  # Amount

            # Ensure 'QuantityIssued' for the dictionary can be "" if originally None or non-numeric string
            # If your front-end expects an empty string, keep this logic
            display_quantity_issued = (
                ""
                if r[8] is None or not isinstance(r[8], (int, float, decimal.Decimal))
                else quantity_issued_val
            )

            # Calculate Total - ensuring we use the float versions for calculation
            total_calc = None
            if quantity_issued_val is None:  # If QuantityIssued was NULL/None from DB
                total_calc = amount_val
            elif amount_val is not None:  # Ensure Amount is not None for multiplication
                total_calc = round(quantity_issued_val * amount_val, 2)
            # If amount_val is None and quantity_issued_val is not None, total_calc would remain None

            result.append(
                {
                    "Fullname": r[0],
                    "MakeAndModel": r[1],
                    "RegNo": r[2],
                    "Date": r[3],
                    "ChassisNo": r[4],
                    "EngineCode": r[5],
                    "Mileage": r[6],
                    "Item": r[7],
                    "QuantityIssued": display_quantity_issued,  # Use the potentially "" value for display
                    "Amount": amount_val,  # This is now always a float or None
                    "AssignedJobID": r[10],
                    "Total": total_calc,  # This is now always a float or None
                }
            )

        return result



@anvil.server.callable()
def get_invoice_details_by_job_id(job_id):
    with db_cursor() as cursor:
        query = """
                SELECT 
                    tbl_clientcontacts.Fullname, 
                    tbl_jobcarddetails.MakeAndModel, 
                    tbl_jobcarddetails.RegNo, 
                    tbl_invoices.Date, 
                    tbl_jobcarddetails.ChassisNo, 
                    tbl_jobcarddetails.EngineCode, 
                    tbl_jobcarddetails.Mileage, 
                    tbl_invoices.Item, 
                    tbl_invoices.QuantityIssued, 
                    tbl_invoices.Amount, 
                    tbl_invoices.AssignedJobID,
                    tbl_invoices.Part_No,
                    tbl_carpartnames.ID AS CarPartID   -- ✅ new column
                FROM 
                    (tbl_jobcarddetails 
                    INNER JOIN tbl_clientcontacts 
                        ON tbl_jobcarddetails.ClientDetails = tbl_clientcontacts.ID) 
                INNER JOIN tbl_invoices 
                    ON tbl_jobcarddetails.ID = tbl_invoices.AssignedJobID
                LEFT JOIN tbl_carpartnames   -- ✅ join to match PartNo
                    ON tbl_invoices.Part_No = tbl_carpartnames.PartNo
                WHERE 
                    tbl_invoices.AssignedJobID = %s
                ORDER BY 
                    tbl_invoices.ID 

        """
        cursor.execute(query, (job_id,))
        rows = cursor.fetchall()

        result = []
        for r in rows:
            # Helper function to ensure we get a float from various types
            def safe_float_convert(value):
                if value is None:
                    return None  # Or 0.0, depending on desired behavior for NULLs
                if isinstance(value, (int, float, decimal.Decimal)):
                    return float(value)
                # If it's a string, try to clean it and convert
                if isinstance(value, str):
                    try:
                        return float(value.replace(",", ""))
                    except ValueError:
                        # Handle cases where string cannot be converted (e.g., non-numeric string)
                        print(f"Warning: Could not convert string '{value}' to float.")
                        return None  # Or raise an error
                return None  # Default if type is unexpected

            quantity_issued_val = safe_float_convert(r[8])  # QuantityIssued
            amount_val = safe_float_convert(r[9])  # Amount

            # Ensure 'QuantityIssued' for the dictionary can be "" if originally None or non-numeric string
            # If your front-end expects an empty string, keep this logic
            display_quantity_issued = (
                ""
                if r[8] is None or not isinstance(r[8], (int, float, decimal.Decimal))
                else quantity_issued_val
            )

            # Calculate Total - ensuring we use the float versions for calculation
            total_calc = None
            if quantity_issued_val is None:  # If QuantityIssued was NULL/None from DB
                total_calc = amount_val
            elif amount_val is not None:  # Ensure Amount is not None for multiplication
                total_calc = round(quantity_issued_val * amount_val, 2)
            # If amount_val is None and quantity_issued_val is not None, total_calc would remain None

            result.append(
                {
                    "Fullname": r[0],
                    "MakeAndModel": r[1],
                    "RegNo": r[2],
                    "Date": r[3],
                    "ChassisNo": r[4],
                    "EngineCode": r[5],
                    "Mileage": r[6],
                    "Item": r[7],
                    "QuantityIssued": display_quantity_issued,  # Use the potentially "" value for display
                    "Amount": amount_val,  # This is now always a float or None
                    "AssignedJobID": r[10],
                    "Total": total_calc,  # This is now always a float or None
                }
            )

        return result

@anvil.server.callable()
def fillQuotationInvoiceData(
    jobCardID, docType, logo_path: str = os.getenv("LOGO"),font_path: str = os.getenv("FONT_PATH")
) -> str:
    if docType == "Quotation":
        docTitle = "Quotation"
        vehicledetails = get_quote_details_by_job_id(jobCardID)
    elif docType == "InterimQuotation":
        docTitle = "Interim Quotation"
        vehicledetails = get_quote_details_by_job_id(jobCardID)
    elif docType == "Invoice":
        docTitle = "Invoice"
        vehicledetails = get_invoice_details_by_job_id(jobCardID)
    elif docType == "Confirm Quotation":
        docTitle = "Confirm Quotation"
        vehicledetails = get_quote_confirmation_details_by_job_id(jobCardID)

    # === Embed MozillaHeadline font as base64 ===
    font_base64 = ""
    if font_path and os.path.exists(font_path):
        with open(font_path, "rb") as f:
            font_base64 = base64.b64encode(f.read()).decode("utf-8")

    # === Handle company logo ===
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
        logo_img_tag = f'<img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="width: 100%; height: 100%; border-radius: 2px;">'
    else:
        logo_img_tag = "LOGO"

    # Calculate grand total
    sub_total = sum(float(item["Total"]) for item in vehicledetails)
    for item in vehicledetails:
        if item["Item"] == "Previous Balance":
            previous_balance = item["Amount"]
            sub_total = (
                sub_total - item["Amount"]
            )  # Get sub total without previous balance
            footer_total_details = f"""
                        <tr class="total-row">
                            <td colspan="4" style="text-align: right; font-weight: 500;">Sub Total</td>
                            <td style="font-weight: 500;">{sub_total:,.2f}</td>                    
                        </tr>
                        <tr class="total-row">
                            <td colspan="4" style="text-align: right; font-weight: 500;">Previous Balance</td>
                            <td style="font-weight: 500;">{previous_balance:,.2f}</td>
                        </tr>       
                """

        else:
            previous_balance = 0
            footer_total_details = ""

    grand_total = sub_total + float(previous_balance)

    # Generate items table rows
    items_html = ""
    counter = 0
    for item in vehicledetails:
        counter = counter + 1
        if item["Amount"] == 0:  # Implies To Be Confirmed
            textAmount = "TO BE CONFIRMED"
        else:
            textAmount = f"{item['Amount']:,.2f}"
        if item["Total"] == 0:  # Implies To Be Confirmed
            textTotal = "TO BE CONFIRMED"
        else:
            textTotal = f"{item['Total']:,.2f}"

        # Do not display Previous balance in the table
        if item["Item"] != "Previous Balance":

            items_html += f"""
                    <tr class="item-row">
                        <td>{counter}</td>
                        <td>{item['Item']}</td>
                        <td>{item['QuantityIssued']}</td>
                        <td>{textAmount}</td>
                        <td>{textTotal}</td>
                    </tr>"""

    if docType in ("Quotation", "InterimQuotation"):
        quotationNotes = """
                    <div class="notes-section">
                        <div class="notes-title">NOTE: THE ABOVE ESTIMATE IS SUBJECT TO REVIEW DUE TO:</div>
                        <ol class="notes-list">
                            <li>Price change at the time of actual repair</li>
                            <li>Further damages found during repairs</li>
                            <li>100% Deposit on imported parts</li>
                            <li>70% deposit on local parts on commencement</li>
                        </ol>
                    </div>
        """
    else:
        quotationNotes = """
                    <div class="notes-section">
                        <div class="notes-title">NOTES: </div>
                        <ol class="notes-list">
                            <li>Thank you for choosing BMW CENTER LIMITED</li>
                            <li>M-Pesa Paybill Number: 529914 \n
				                Account Number:   155393</li>
                            <li>Cheque Address to: BMW CENTER LIMITED</li>
                         </ol>
                    </div>
            """

        # Complete HTML template with fixed structure
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{docTitle}</title>
    <style>
        /* --- Embed Mozilla Headline font --- */
        @font-face {{
            font-family: 'Mozilla Headline';
            src: url(data:font/ttf;base64,{font_base64}) format('truetype');
        }}
        body {{
            font-family: Roboto, Noto, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.4286;
            background-color: #fafafa;
            margin: 0;
            padding: 16px;
        }}

        .quotation-container {{
            background-color: white;
            border-radius: 2px;
            box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                        0 3px 1px -2px rgba(0, 0, 0, 0.2),
                        0 1px 5px 0 rgba(0, 0, 0, 0.12);
            max-width: 800px;
            margin: 0 auto;
            overflow: hidden;
        }}

        .logo-section {{
            text-align: center;
            padding: 24px;
            background-color: white;
            border-bottom: 1px solid #e0e0e0;
        }}

        .logo-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-bottom: 16px;
        }}

        .logo-image {{
            width: 725px;
            height: 100px;
            background: linear-gradient(135deg, #228B22, #90EE90, #FFD700, #FF6347);
            border-radius: 2px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: white;
            font-weight: 500;
            box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                        0 3px 1px -2px rgba(0, 0, 0, 0.2),
                        0 1px 5px 0 rgba(0, 0, 0, 0.12);
        }}

        .header {{
            background-color: #000;
            color: white;
            text-align: center;
            padding: 16px 24px;
            font-size: 16px;
            font-weight: 300;
            letter-spacing: .5px;
            box-shadow: 0 4px 5px 0 rgba(0, 0, 0, 0.14),
                        0 1px 10px 0 rgba(0, 0, 0, 0.12),
                        0 2px 4px -1px rgba(0, 0, 0, 0.2);
        }}

        .detail-row {{
            display: grid;
            grid-template-columns: 140px 1fr; /* label column, value column */
            column-gap: 8px;
            margin-bottom: 12px;
        }}

        .detail-label {{
                font-weight: bold;
                font-size: 16px;
                color: rgba(0,0,0,0.87);
                
        }}

        .detail-value {{
            font-size: 16px;
            color: rgba(0,0,0,0.87);
            text-align: left;
            
        }}

        .items-table {{
            border-collapse: collapse;
            width: 100%;
            margin: 0 24px 24px 0;
            background-color: white;
            border-radius: 2px;
            overflow: hidden;
            box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                        0 3px 1px -2px rgba(0, 0, 0, 0.2),
                        0 1px 5px 0 rgba(0, 0, 0, 0.12);
        }}

        .items-table th {{
            background-color: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
            padding: 16px;
            text-align: left;
            font-weight: bold;
            font-size: 14px;
            color: rgba(0,0,0,0.87);
            text-transform: uppercase;
            letter-spacing: .5px;
           
        }}

        .items-table td {{
            border-bottom: 1px solid rgba(0,0,0,0.12);
            padding: 16px;
            font-size: 14px;
            color: rgba(0,0,0,0.87);
            
        }}

        .items-table .item-row:hover {{
            background-color: rgba(0,0,0,0.04);
        }}

        .total-row {{
            background-color: #000 !important;
            color: white !important;
        }}

        .total-row td {{
            border-bottom: none !important;
            font-weight: 300;
            font-size: 16px;
            color: white !important;
            padding: 16px;
            
        }}

        .notes-section {{
            padding: 24px;
            background-color: #f5f5f5;
            margin-top: 16px;
        }}

        .notes-title {{
            margin-bottom: 16px;
            font-weight: 500;
            font-size: 16px;
            color: rgba(0,0,0,0.87);
            font-family: 'Mozilla Headline';
        }}

        .notes-list {{
            margin: 0;
            padding-left: 24px;
            color: rgba(0,0,0,0.74);
        }}

        .notes-list li {{
            margin-bottom: 8px;
            line-height: 1.5;
            font-family: 'Mozilla Headline';
        }}
        #footer  div {{
                width: 80%;
                margin: 0 auto;
                text-align: center;
                font-size: 12px;
                font-family: 'Mozilla Headline';
            }}
    </style>
    
</head>
<body>
    <div class="quotation-container">
        <div class="logo-section">
            <div class="logo-container">
                <div class="logo-image">
                    {logo_img_tag}
                </div>
            </div>
        </div>

        <div class="header">
            {docTitle.upper()}
        </div>

        <!-- UPDATED: Replaced details-section div with table layout -->
        <table style="width: 100%; table-layout: fixed; margin: 24px 0;">
            <tr>
                <!-- Left Column -->
                <td style="width: 50%; vertical-align: top; padding-left: 24px; padding-right: 32px;">
                    <div class="detail-row">
                        <span class="detail-label">Customer Name:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['Fullname']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Make And Model:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['MakeAndModel']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Reg No:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['RegNo']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Date:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['Date']}</span>
                        </div>
                    </div>
                </td>

                <!-- Right Column -->
                <td style="width: 50%; vertical-align: top; padding-left: 32px;">
                    <div class="detail-row">
                        <span class="detail-label">Chassis:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['ChassisNo']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Engine:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['EngineCode']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Mileage:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['Mileage']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">&nbsp;</span>
                        <span class="detail-value">&nbsp;</span>
                    </div>
                </td>
            </tr>
        </table>
        <!-- END UPDATED -->

        <table class="items-table">
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Item</th>
                    <th>Quantity</th>
                    <th>Amount (Kshs)</th>
                    <th>Total (Kshs)</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
                {footer_total_details}
                
                <tr class="total-row">
                    <td colspan="4" style="text-align: right; font-weight: 500;">Grand Total</td>
                    <td style="font-weight: 500;">{grand_total:,.2f}</td>
                </tr>
                
            </tbody>
        </table>
    {quotationNotes} 
   <footer id="footer">
        <div> 
            <p>Joy Is The Feeling Of Being Looked After By The Best - BMW CENTER For Your BMW.</p>
        </div>
    </footer>
    </div>
    </body>
    </html>"""

    return html_content

# *************************************************** BMA Messenger Application - Payment Details Section ************************************************
@anvil.server.callable()
def getPaymentsDetails(paymentID):
    with db_cursor() as cursor:
        query = """
                            SELECT
                                p.Date,
                                j.JobCardRef,
                                p.PaymentMode,
                                SUM(
                                    COALESCE(i.QuantityIssued, 1) * i.Amount
                                ) AS InvoiceAmount,
                                p.AmountPaid,
                                p.Discount,
                                p.Balance
                            FROM
                                tbl_payments AS p
                            JOIN tbl_jobcarddetails AS j
                              ON p.JobCardRefID = j.ID
                            JOIN tbl_invoices AS i
                              ON j.ID = i.AssignedJobID
                            WHERE p.JobCardRefID = %s
                            GROUP BY
                                p.ID,
                                p.Date,
                                j.JobCardRef,
                                p.PaymentMode,
                                p.AmountPaid,
                                p.Discount,
                                p.Balance
                            ORDER BY
                                p.Date DESC
                        """
        cursor.execute(query, (paymentID,))
        rows = cursor.fetchall()
        # Convert rows to a list of dictionaries
        result = [
            {
                "No": index + 1,
                "Date": row[0],
                "JobCardRef": row[1],
                "PaymentMode": row[2],
                "InvoiceAmount": f"{float(row[3]):,.2f}" if row[3] is not None else 0.0,
                "AmountPaid": f"{float(row[4]):,.2f}" if row[4] is not None else 0.0,
                "Discount": f"{float(row[5]):,.2f}" if row[5] is not None else 0.0,
                "Balance": f"{float(row[6]):,.2f}" if row[6] is not None else 0.0,
            }
            for index, row in enumerate(rows)
        ]

        return result
    
@anvil.server.callable()
def fillReportData(jobCardID, docType, logo_path: str = os.getenv("LOGO"),font_path: str = os.getenv("FONT_PATH")) -> str:
    if docType == "Payment":
        docTitle = "Payment Details"
        reportdetails = getPaymentsDetails(jobCardID)
        vehicledetails = get_invoice_details_by_job_id(jobCardID)

    # === Embed MozillaHeadline font as base64 ===
    font_base64 = ""
    if font_path and os.path.exists(font_path):
        with open(font_path, "rb") as f:
            font_base64 = base64.b64encode(f.read()).decode("utf-8")

    # === Handle company logo ===
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
        logo_img_tag = f'<img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="width: 100%; height: 100%; border-radius: 2px;">'
    else:
        logo_img_tag = "LOGO"

    # Generate items table rows
    items_html = ""
    counter = 0
    for item in reportdetails:
        counter = counter + 1
        items_html += f"""
                    <tr class="item-row">
                        <td>{counter}</td>
                        <td>{item['Date']}</td>
                        <td>{item['JobCardRef']}</td>
                        <td>{item['PaymentMode']}</td>
                        <td>{item['InvoiceAmount']}</td>
                        <td>{item['AmountPaid']}</td>
                        <td>{item['Discount']}</td>
                        <td>{item['Balance']}</td>
                    </tr>"""

        # Complete HTML template with fixed structure
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{docTitle}</title>
    <style>
        /* --- Embed Mozilla Headline font --- */
        @font-face {{
            font-family: 'Mozilla Headline';
            src: url(data:font/ttf;base64,{font_base64}) format('truetype');
        }}
        body {{
            font-family: Roboto, Noto, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.4286;
            background-color: #fafafa;
            margin: 0;
            padding: 16px;
        }}

        .quotation-container {{
            background-color: white;
            border-radius: 2px;
            box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                        0 3px 1px -2px rgba(0, 0, 0, 0.2),
                        0 1px 5px 0 rgba(0, 0, 0, 0.12);
            max-width: 800px;
            margin: 0 auto;
            overflow: hidden;
        }}

        .logo-section {{
            text-align: center;
            padding: 24px;
            background-color: white;
            border-bottom: 1px solid #e0e0e0;
        }}

        .logo-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-bottom: 16px;
        }}

        .logo-image {{
            width: 725px;
            height: 100px;
            background: linear-gradient(135deg, #228B22, #90EE90, #FFD700, #FF6347);
            border-radius: 2px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: white;
            font-weight: 500;
            box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                        0 3px 1px -2px rgba(0, 0, 0, 0.2),
                        0 1px 5px 0 rgba(0, 0, 0, 0.12);
        }}

        .header {{
            background-color: #000;
            color: white;
            text-align: center;
            padding: 16px 24px;
            font-size: 16px;
            font-weight: 300;
            letter-spacing: .5px;
            box-shadow: 0 4px 5px 0 rgba(0, 0, 0, 0.14),
                        0 1px 10px 0 rgba(0, 0, 0, 0.12),
                        0 2px 4px -1px rgba(0, 0, 0, 0.2);
        }}

        .detail-row {{
            display: grid;
            grid-template-columns: 140px 1fr; /* label column, value column */
            column-gap: 8px;
            margin-bottom: 12px;
        }}

        .detail-label {{
                font-weight: bold;
                font-size: 16px;
                color: rgba(0,0,0,0.87);
                
        }}

        .detail-value {{
            font-size: 16px;
            color: rgba(0,0,0,0.87);
            text-align: left;
            
        }}

        .items-table {{
            border-collapse: collapse;
            width: 100%;
            margin: 0 24px 24px 0;
            background-color: white;
            border-radius: 2px;
            overflow: hidden;
            box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                        0 3px 1px -2px rgba(0, 0, 0, 0.2),
                        0 1px 5px 0 rgba(0, 0, 0, 0.12);
        }}

        .items-table th {{
            background-color: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
            padding: 16px;
            text-align: left;
            font-weight: bold;
            font-size: 14px;
            color: rgba(0,0,0,0.87);
            text-transform: uppercase;
            letter-spacing: .5px;
            
        }}

        .items-table td {{
            border-bottom: 1px solid rgba(0,0,0,0.12);
            padding: 16px;
            font-size: 14px;
            color: rgba(0,0,0,0.87);
           
        }}

        .items-table .item-row:hover {{
            background-color: rgba(0,0,0,0.04);
        }}

        .total-row {{
            background-color: #000 !important;
            color: white !important;
        }}

        .total-row td {{
            border-bottom: none !important;
            font-weight: 300;
            font-size: 16px;
            color: white !important;
            padding: 16px;
           
        }}

        .notes-section {{
            padding: 24px;
            background-color: #f5f5f5;
            margin-top: 16px;
        }}

        .notes-title {{
            margin-bottom: 16px;
            font-weight: 500;
            font-size: 16px;
            color: rgba(0,0,0,0.87);
            font-family: 'Mozilla Headline';
        }}

        .notes-list {{
            margin: 0;
            padding-left: 24px;
            color: rgba(0,0,0,0.74);
        }}

        .notes-list li {{
            margin-bottom: 8px;
            line-height: 1.5;
            font-family: 'Mozilla Headline';
        }}
        #footer  div {{
                width: 80%;
                margin: 0 auto;
                text-align: center;
                font-size: 12px;
                font-family: 'Mozilla Headline';
            }}
    </style>
</head>
<body>
    <div class="quotation-container">
        <div class="logo-section">
            <div class="logo-container">
                <div class="logo-image">
                    {logo_img_tag}
                </div>
            </div>
        </div>

        <div class="header">
            {docTitle.upper()}
        </div>
         <!-- UPDATED: Replaced details-section div with table layout -->
        <table style="width: 100%; table-layout: fixed; margin: 24px 0;">
            <tr>
                <!-- Left Column -->
                <td style="width: 50%; vertical-align: top; padding-left: 24px; padding-right: 32px;">
                    <div class="detail-row">
                        <span class="detail-label">Customer Name:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['Fullname']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Make And Model:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['MakeAndModel']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Reg No:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['RegNo']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Date:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['Date']}</span>
                        </div>
                    </div>
                </td>

                <!-- Right Column -->
                <td style="width: 50%; vertical-align: top; padding-left: 32px;">
                    <div class="detail-row">
                        <span class="detail-label">Chassis:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['ChassisNo']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Engine:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['EngineCode']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Mileage:</span>
                        <div>
                        <span class="detail-value">{vehicledetails[0]['Mileage']}</span>
                        </div>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">&nbsp;</span>
                        <span class="detail-value">&nbsp;</span>
                    </div>
                </td>
            </tr>
        </table>
        <!-- END UPDATED -->

        <table class="items-table">
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Date</th>
                    <th>Ref</th>
                    <th>Mode</th>
                    <th>Invoiced</th>
                    <th>Paid</th>
                    <th>Discount</th>
                    <th>Balance</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        <footer id="footer">
        <div> 
            <p>Joy Is The Feeling Of Being Looked After By The Best - BMW CENTER For Your BMW.</p>
        </div>
    </footer>    
    </div>
    </body>
    </html>"""

    return html_content

# ********************************************Defects List Section ************************************
@anvil.server.callable()
def get_defects_list_details_by_job_id(jobCardID):
    """
    Returns detailed job card information including:
      - Client name
      - Vehicle details
      - Technician name
      - Cleaned and enumerated defects list
    """
    with db_cursor() as cursor:
        query1 = """
            SELECT 
                tbl_clientcontacts.Fullname AS ClientName,
                tbl_jobcarddetails.RegNo,
                tbl_jobcarddetails.MakeAndModel,
                tbl_jobcarddetails.EngineCode,
                tbl_jobcarddetails.ChassisNo,
                tbl_jobcarddetails.ReceivedDate,
                tbl_technicians.Fullname AS TechnicianName,
                tbl_techniciandefectsandrequestedparts.Defects,
                tbl_checkstaff.Staff AS PreparedByStaff,
                tbl_techniciandefectsandrequestedparts.Signature
            FROM tbl_jobcarddetails
            JOIN tbl_clientcontacts 
                ON tbl_clientcontacts.ID = tbl_jobcarddetails.ClientDetails
            JOIN tbl_pendingassignedjobs 
                ON tbl_pendingassignedjobs.JobCardRefID = tbl_jobcarddetails.ID
            JOIN tbl_technicians 
                ON tbl_technicians.ID = tbl_pendingassignedjobs.TechnicianID
            JOIN tbl_techniciandefectsandrequestedparts 
                ON tbl_techniciandefectsandrequestedparts.JobCardRefID = tbl_jobcarddetails.ID
            JOIN tbl_checkstaff
                ON tbl_checkstaff.Staff = tbl_techniciandefectsandrequestedparts.PreparedByStaff
            WHERE tbl_jobcarddetails.ID = %s;

        """
        cursor.execute(query1, (jobCardID,))
        result1 = cursor.fetchone()

        query2 = """
            SELECT 
                tbl_clientcontacts.Fullname AS ClientName,
                tbl_jobcarddetails.RegNo,
                tbl_jobcarddetails.MakeAndModel,
                tbl_jobcarddetails.EngineCode,
                tbl_jobcarddetails.ChassisNo,
                tbl_jobcarddetails.ReceivedDate,
                tbl_technicians.Fullname AS TechnicianName,
                tbl_techniciandefectsandrequestedparts.Defects,
                tbl_technicians.Fullname AS PreparedByStaff,
                tbl_techniciandefectsandrequestedparts.Signature
            FROM tbl_jobcarddetails
            JOIN tbl_clientcontacts 
                ON tbl_clientcontacts.ID = tbl_jobcarddetails.ClientDetails
            JOIN tbl_pendingassignedjobs 
                ON tbl_pendingassignedjobs.JobCardRefID = tbl_jobcarddetails.ID
            JOIN tbl_techniciandefectsandrequestedparts 
                ON tbl_techniciandefectsandrequestedparts.JobCardRefID = tbl_jobcarddetails.ID
            JOIN tbl_technicians
                ON tbl_technicians.Fullname = tbl_techniciandefectsandrequestedparts.PreparedByStaff
            WHERE tbl_jobcarddetails.ID = %s;
            """
        cursor.execute(query2, (jobCardID,))
        result2 = cursor.fetchone()
        if result1 is None and result2 is None:
            return None  # No data found for the given JobCardID
        elif result1 is not None:
            result = result1
        else:
            result = result2

        # Unpack query result
        (
            client_name,
            reg_no,
            make_model,
            engine_code,
            chassis_no,
            received_date,
            technician_name,
            raw_defects,
            staff,
            signature,
        ) = result

        # --- Clean and process defects text ---
        if raw_defects:
            # Step 1: Remove HTML tags (<div>, <br>, etc.)
            text_only = re.sub(r"<[^>]+>", "", raw_defects)

            # Step 2: Split into lines, remove empty ones
            lines = [line.strip() for line in text_only.splitlines() if line.strip()]

            # Step 3: Enumerate defects
            numbered_defects = [
                {"No": i + 1, "Defect": line} for i, line in enumerate(lines)
            ]
        else:
            numbered_defects = []

        # If Signature is stored as BLOB → convert to base64
        signature_b64 = ""
        if isinstance(signature, (bytes, bytearray)):
            signature_b64 = base64.b64encode(signature).decode("utf-8")

        # --- Return combined data ---
        return {
            "ClientName": client_name,
            "RegNo": reg_no,
            "MakeAndModel": make_model,
            "EngineCode": engine_code,
            "ChassisNo": chassis_no,
            "ReceivedDate": str(received_date),
            "TechnicianName": technician_name,
            "Defects": numbered_defects,
            "Staff": staff,
            "Signature": signature_b64,
        }


@anvil.server.callable()
def fillDefectsListFormData(
    jobCardID, docType, logo_path: str = os.getenv("LOGO"),font_path: str = os.getenv("FONT_PATH")
) -> str:
    if docType == "DefectsList":
        docTitle = "Defects List"
        defectsdetails = get_defects_list_details_by_job_id(jobCardID)

    # === Embed MozillaHeadline font as base64 ===

    font_base64 = ""
    if font_path and os.path.exists(font_path):
        with open(font_path, "rb") as f:
            font_base64 = base64.b64encode(f.read()).decode("utf-8")

    # === Handle company logo ===
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
        logo_img_tag = f'<img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="width: 100%; height: 100%; border-radius: 2px;">'
    else:
        logo_img_tag = "LOGO"

    # === Generate defects rows ===
    items_html = ""
    for item in defectsdetails["Defects"]:
        items_html += f"""
            <tr class="item-row">
                <td>{item["No"]}</td>
                <td>{item["Defect"]}</td>
            </tr>"""

    # === Signature ===
    signature_html = f"""
        <img src="data:image/png;base64,{defectsdetails["Signature"]}" 
             alt="Client Signature" 
             style="max-height:100px; border:1px solid #ccc; padding:4px;"/>
    """

    # === Full HTML ===
    html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{docTitle}</title>
            <style>
                /* --- Embed Mozilla Headline font --- */
                @font-face {{
                    font-family: 'Mozilla Headline';
                    src: url(data:font/ttf;base64,{font_base64}) format('truetype');
                }}

                body {{
                    font-family: 'Roboto', 'Noto', Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.4286;
                    background-color: #fafafa;
                    margin: 0;
                    padding: 16px;
                }}

                .quotation-container {{
                    background-color: white;
                    border-radius: 2px;
                    box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                                0 3px 1px -2px rgba(0, 0, 0, 0.2),
                                0 1px 5px 0 rgba(0, 0, 0, 0.12);
                    max-width: 800px;
                    margin: 0 auto;
                    overflow: hidden;
                }}

                .logo-section {{
                    text-align: center;
                    padding: 24px;
                    background-color: white;
                    border-bottom: 1px solid #e0e0e0;
                }}

                .logo-container {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 20px;
                    margin-bottom: 16px;
                }}

                .logo-image {{
                    width: 725px;
                    height: 100px;
                    background: linear-gradient(135deg, #228B22, #90EE90, #FFD700, #FF6347);
                    border-radius: 2px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                    color: white;
                    font-weight: 500;
                    box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                                0 3px 1px -2px rgba(0, 0, 0, 0.2),
                                0 1px 5px 0 rgba(0, 0, 0, 0.12);
                }}

                .header {{
                    background-color: #000;
                    color: white;
                    text-align: center;
                    padding: 16px 24px;
                    font-size: 16px;
                    font-weight: 300;
                    letter-spacing: .5px;
                    box-shadow: 0 4px 5px 0 rgba(0, 0, 0, 0.14),
                                0 1px 10px 0 rgba(0, 0, 0, 0.12),
                                0 2px 4px -1px rgba(0, 0, 0, 0.2);
                }}

                .detail-row {{
                    display: grid;
                    grid-template-columns: 140px 1fr;
                    column-gap: 8px;
                    margin-bottom: 12px;
                }}

                .detail-label {{
                    font-weight: bold;
                    font-size: 16px;
                    color: rgba(0,0,0,0.87);
                }}

                .detail-value {{
                    font-size: 16px;
                    color: rgba(0,0,0,0.87);
                    text-align: left;
                }}

                .items-table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 0 24px 24px 0;
                    background-color: white;
                    border-radius: 2px;
                    overflow: hidden;
                    box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                                0 3px 1px -2px rgba(0, 0, 0, 0.2),
                                0 1px 5px 0 rgba(0, 0, 0, 0.12);
                }}

                .items-table th {{
                    background-color: #f5f5f5;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 16px;
                    text-align: left;
                    font-weight: bold;
                    font-size: 14px;
                    color: rgba(0,0,0,0.87);
                    text-transform: uppercase;
                    letter-spacing: .5px;
                }}

                .items-table td {{
                    border-bottom: 1px solid rgba(0,0,0,0.12);
                    padding: 16px;
                    font-size: 14px;
                    color: rgba(0,0,0,0.87);
                }}

                .items-table .item-row:hover {{
                    background-color: rgba(0,0,0,0.04);
                }}

                .notes-title, .notes-list li, #footer div {{
                    font-family: 'Mozilla Headline', Arial, sans-serif;
                }}

                #footer div {{
                    width: 80%;
                    margin: 0 auto;
                    text-align: center;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="quotation-container">
                <div class="logo-section">
                    <div class="logo-container">
                        <div class="logo-image">
                            {logo_img_tag}
                        </div>
                    </div>
                </div>

                <div class="header">{docTitle.upper()}</div>

                <table style="width: 100%; table-layout: fixed; margin: 24px 0;">
                    <tr>
                        <td style="width: 50%; vertical-align: top; padding-left: 24px; padding-right: 32px;">
                            <div class="detail-row"><span class="detail-label">Customer Name:</span><div><span class="detail-value">{defectsdetails['ClientName']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Make And Model:</span><div><span class="detail-value">{defectsdetails['MakeAndModel']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Reg No:</span><div><span class="detail-value">{defectsdetails['RegNo']}</span></div></div>
                        </td>
                        <td style="width: 50%; vertical-align: top; padding-left: 32px;">
                            <div class="detail-row"><span class="detail-label">Engine:</span><div><span class="detail-value">{defectsdetails['EngineCode']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Chassis:</span><div><span class="detail-value">{defectsdetails['ChassisNo']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Date:</span><div><span class="detail-value">{defectsdetails['ReceivedDate']}</span></div></div>
                        </td>
                    </tr>
                </table>

                <table class="items-table">
                    <thead><tr><th>No.</th><th>Defects</th></tr></thead>
                    <tbody>{items_html}</tbody>
                </table>

                <table style="width: 100%; table-layout: fixed; margin: 24px 0;">
                    <tr>
                        <td style="width: 33.33%; vertical-align: top; padding: 0 16px;">
                            <div class="detail-row"><span class="detail-label">Prepared By:</span><div><span class="detail-value">{defectsdetails['Staff']}</span></div></div>
                        </td>
                        <td style="width: 33.33%; vertical-align: top; padding: 0 16px;">
                            <div class="detail-row"><span class="detail-label">Signature:</span><div><span class="detail-value">{signature_html}</span></div></div>
                        </td>
                    </tr>
                </table>

                <footer id="footer">
                    <div><p>Joy Is The Feeling Of Being Looked After By The Best - BMW CENTER For Your BMW.</p></div>
                </footer>
            </div>
        </body>
        </html>
    """

    return html_content

# ********************************************End- Defects List Section ************************************

# ********************************************Start - Tech Notes Section ************************************
@anvil.server.callable()
def get_tech_notes_details_by_job_id(jobCardID):
    """
    Returns detailed job card information including:
      - Client name
      - Vehicle details
      - Technician name
      - Cleaned and enumerated technician's notes
    """
    with db_cursor() as cursor:
        query = """
            SELECT 
                tbl_clientcontacts.Fullname AS ClientName,
                tbl_jobcarddetails.RegNo,
                tbl_jobcarddetails.MakeAndModel,
                tbl_jobcarddetails.EngineCode,
                tbl_jobcarddetails.ChassisNo,
                tbl_jobcarddetails.ReceivedDate,
                tbl_technicians.Fullname AS TechnicianName,
                tbl_jobcarddetails.Notes
            FROM tbl_jobcarddetails
            JOIN tbl_clientcontacts 
                ON tbl_clientcontacts.ID = tbl_jobcarddetails.ClientDetails
            JOIN tbl_pendingassignedjobs 
                ON tbl_pendingassignedjobs.JobCardRefID = tbl_jobcarddetails.ID
            JOIN tbl_technicians 
                ON tbl_technicians.ID = tbl_pendingassignedjobs.TechnicianID
            WHERE tbl_jobcarddetails.ID = %s;

        """
        cursor.execute(query, (jobCardID,))
        result = cursor.fetchone()

        if not result:
            return None

        # Unpack query result
        (
            client_name,
            reg_no,
            make_model,
            engine_code,
            chassis_no,
            received_date,
            technician_name,
            notes,
        ) = result

        # --- Clean and process notes text ---
        if notes:
            # Step 1: Remove HTML tags (<div>, <br>, etc.)
            text_only = re.sub(r"<[^>]+>", "", notes)

            # Step 2: Split into lines, remove empty ones
            lines = [line.strip() for line in text_only.splitlines() if line.strip()]

            # Step 3: Enumerate notes
            numbered_notes = [
                {"No": i + 1, "Notes": line} for i, line in enumerate(lines)
            ]
        else:
            numbered_notes = []


        # --- Return combined data ---
        return {
            "ClientName": client_name,
            "RegNo": reg_no,
            "MakeAndModel": make_model,
            "EngineCode": engine_code,
            "ChassisNo": chassis_no,
            "ReceivedDate": str(received_date),
            "TechnicianName": technician_name,
            "Notes": numbered_notes,
        }
    
@anvil.server.callable()
def fillTechNotesFormData(jobCardID, docType, logo_path: str = os.getenv("LOGO"),font_path: str = os.getenv("FONT_PATH")) -> str:
    if docType == "TechNotes":
        docTitle = "Technician Notes"
        technotes = get_tech_notes_details_by_job_id(jobCardID)

    # === Embed MozillaHeadline font as base64 ===
    font_base64 = ""
    if font_path and os.path.exists(font_path):
        with open(font_path, "rb") as f:
            font_base64 = base64.b64encode(f.read()).decode("utf-8")

    # === Handle company logo ===
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
        logo_img_tag = f'<img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="width: 100%; height: 100%; border-radius: 2px;">'
    else:
        logo_img_tag = "LOGO"

    # === Generate defects rows ===
    items_html = ""
    for item in technotes["Notes"]:
        items_html += f"""
        <tr class="item-row">
            <td>{item["No"]}</td>
            <td>{item["Notes"]}</td>
        </tr>"""

    # === Full HTML ===
    html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{docTitle}</title>
            <style>
                /* --- Embed Mozilla Headline font --- */
                @font-face {{
                    font-family: 'Mozilla Headline';
                    src: url(data:font/ttf;base64,{font_base64}) format('truetype');
                }}

                body {{
                    font-family: 'Roboto', 'Noto', Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.4286;
                    background-color: #fafafa;
                    margin: 0;
                    padding: 16px;
                }}

                .quotation-container {{
                    background-color: white;
                    border-radius: 2px;
                    box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                                0 3px 1px -2px rgba(0, 0, 0, 0.2),
                                0 1px 5px 0 rgba(0, 0, 0, 0.12);
                    max-width: 800px;
                    margin: 0 auto;
                    overflow: hidden;
                }}

                .logo-section {{
                    text-align: center;
                    padding: 24px;
                    background-color: white;
                    border-bottom: 1px solid #e0e0e0;
                }}

                .logo-container {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 20px;
                    margin-bottom: 16px;
                }}

                .logo-image {{
                    width: 725px;
                    height: 100px;
                    background: linear-gradient(135deg, #228B22, #90EE90, #FFD700, #FF6347);
                    border-radius: 2px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                    color: white;
                    font-weight: 500;
                    box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                                0 3px 1px -2px rgba(0, 0, 0, 0.2),
                                0 1px 5px 0 rgba(0, 0, 0, 0.12);
                }}

                .header {{
                    background-color: #000;
                    color: white;
                    text-align: center;
                    padding: 16px 24px;
                    font-size: 16px;
                    font-weight: 300;
                    letter-spacing: .5px;
                    box-shadow: 0 4px 5px 0 rgba(0, 0, 0, 0.14),
                                0 1px 10px 0 rgba(0, 0, 0, 0.12),
                                0 2px 4px -1px rgba(0, 0, 0, 0.2);
                }}

                .detail-row {{
                    display: grid;
                    grid-template-columns: 140px 1fr;
                    column-gap: 8px;
                    margin-bottom: 12px;
                }}

                .detail-label {{
                    font-weight: bold;
                    font-size: 16px;
                    color: rgba(0,0,0,0.87);
                }}

                .detail-value {{
                    font-size: 16px;
                    color: rgba(0,0,0,0.87);
                    text-align: left;
                }}

                .items-table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 0 24px 24px 0;
                    background-color: white;
                    border-radius: 2px;
                    overflow: hidden;
                    box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                                0 3px 1px -2px rgba(0, 0, 0, 0.2),
                                0 1px 5px 0 rgba(0, 0, 0, 0.12);
                }}

                .items-table th {{
                    background-color: #f5f5f5;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 16px;
                    text-align: left;
                    font-weight: bold;
                    font-size: 14px;
                    color: rgba(0,0,0,0.87);
                    text-transform: uppercase;
                    letter-spacing: .5px;
                }}

                .items-table td {{
                    border-bottom: 1px solid rgba(0,0,0,0.12);
                    padding: 16px;
                    font-size: 14px;
                    color: rgba(0,0,0,0.87);
                }}

                .items-table .item-row:hover {{
                    background-color: rgba(0,0,0,0.04);
                }}

                .notes-title, .notes-list li, #footer div {{
                    font-family: 'Mozilla Headline', Arial, sans-serif;
                }}

                #footer div {{
                    width: 80%;
                    margin: 0 auto;
                    text-align: center;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="quotation-container">
                <div class="logo-section">
                    <div class="logo-container">
                        <div class="logo-image">
                            {logo_img_tag}
                        </div>
                    </div>
                </div>

                <div class="header">{docTitle.upper()}</div>

                <table style="width: 100%; table-layout: fixed; margin: 24px 0;">
                    <tr>
                        <td style="width: 50%; vertical-align: top; padding-left: 24px; padding-right: 32px;">
                            <div class="detail-row"><span class="detail-label">Customer Name:</span><div><span class="detail-value">{technotes['ClientName']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Make And Model:</span><div><span class="detail-value">{technotes['MakeAndModel']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Reg No:</span><div><span class="detail-value">{technotes['RegNo']}</span></div></div>
                        </td>
                        <td style="width: 50%; vertical-align: top; padding-left: 32px;">
                            <div class="detail-row"><span class="detail-label">Engine:</span><div><span class="detail-value">{technotes['EngineCode']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Chassis:</span><div><span class="detail-value">{technotes['ChassisNo']}</span></div></div>
                            <div class="detail-row"><span class="detail-label">Date:</span><div><span class="detail-value">{technotes['ReceivedDate']}</span></div></div>
                        </td>
                    </tr>
                </table>

                <table class="items-table">
                    <thead><tr><th>No.</th><th>Technician Notes</th></tr></thead>
                    <tbody>{items_html}</tbody>
                </table>


                <footer id="footer">
                    <div><p>Joy Is The Feeling Of Being Looked After By The Best - BMW CENTER For Your BMW.</p></div>
                </footer>
            </div>
        </body>
        </html>
    """

    return html_content

# ********************************************End - Tech Notes Section ************************************


@anvil.server.callable()
def createQuotationInvoicePdf(jobCardID, docType):
    try:
        canonical_doc_type = docType
        if not canonical_doc_type:
            raise ValueError(f"Unsupported document type: {docType}")

        docName = anvil.server.call("getQuotationInvoiceName", jobCardID)
        if canonical_doc_type == "Quotation":
            fileName = str(docName) + " Quotation"
        elif canonical_doc_type == "InterimQuotation":
            fileName = str(docName) + " Interim Quote"
        elif canonical_doc_type == "Invoice":
            fileName = str(docName) + " Invoice"
        elif canonical_doc_type == "Confirm Quotation":
            fileName = str(docName) + " Confirm Quotation"
        elif canonical_doc_type == "Payment":
            fileName = str(docName) + " Payment Details"
        elif canonical_doc_type == "DefectsList":
            fileName = str(docName) + " Defects List"
        elif canonical_doc_type == "TechNotes":
            fileName = str(docName) + " Technician Notes"

        setting_options = {
            "encoding": "UTF-8",
            "custom-header": [("Accept-Encoding", "gzip")],
            "page-size": "A4",
            "orientation": "Portrait",
            "margin-top": "0.75in",
            "margin-right": "0.75in",
            "margin-bottom": "0.75in",
            "margin-left": "0.75in",
            "no-outline": False,
            "enable-local-file-access": None,
        }
        if canonical_doc_type == "Payment":
             html_string = fillReportData(jobCardID, canonical_doc_type)
        elif canonical_doc_type == "DefectsList":
            html_string = fillDefectsListFormData(jobCardID, canonical_doc_type)
        elif canonical_doc_type == "TechNotes":
            html_string = fillTechNotesFormData(jobCardID, canonical_doc_type)
        else:
            html_string = fillQuotationInvoiceData(jobCardID, canonical_doc_type)
        pdfkit.from_string(
            html_string, fileName, options=setting_options, configuration=config
        )
        media_object = anvil.media.from_file(fileName, "application/pdf", name=fileName)
        return media_object

    except Exception as e:
        print("PDF generation failed:", str(e))
        raise


def normalize_messenger_document_type(document_value):
    """
    Maps document labels used by SMS rows/mobile app to backend PDF generator doc types.
    """
    if not document_value:
        return None

    normalized = str(document_value).strip().lower()
    if normalized.endswith(".pdf"):
        normalized = normalized[:-4]
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())

    mapping = {
        "quote": "Quotation",
        "interim": "InterimQuotation",
        "invoice": "Invoice",
        "confirm": "Confirm Quotation",
        "payment": "Payment",
        "defects": "DefectsList",
        "notes": "TechNotes",
    }
    return mapping.get(normalized)


# *************************************************** BMA Messenger Application - Download Document Type ************************************************
@anvil.server.callable()
def downloadDocument(jobCardID, documentType=None):
    return anvil.server.call("createQuotationInvoicePdf", jobCardID, documentType)


# *************************************************** BMA Messenger Application - Send SMS Section ************************************************

@anvil.server.http_endpoint('/pending-sms', methods=["GET"])
def get_pending_sms():
    with db_cursor() as cursor:
        # We only fetch records where flag is True (1)
        query = "SELECT id, fullname, phone, message, jobcardrefid, document FROM tbl_sms WHERE flag = True"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convert tuples/dictionaries to a clean list for Android
        pending_messages = []
        for row in rows:
            pending_messages.append(
                {
                "id": row[0] if isinstance(row, tuple) else row['id'],
                "fullname": row[1] if isinstance(row, tuple) else row["fullname"],
                "phone": row[2] if isinstance(row, tuple) else row['phone'],
                "message": row[3] if isinstance(row, tuple) else row['message'],
                "jobcardrefid": row[4] if isinstance(row, tuple) else row['jobcardrefid'],
                "document": row[5] if isinstance(row, tuple) else row['document'],
                "flag": True # Always true because of our SQL filter
                }
            )
        return pending_messages

@anvil.server.http_endpoint('/mark-sent/:msg_id', methods=["POST"])
def mark_sms_sent(msg_id, **kwargs):
    with db_cursor() as cursor:
        query = "UPDATE tbl_sms SET flag = False WHERE id = %s"
        cursor.execute(query, (int(msg_id),))
    return {"status": "success"}

@anvil.server.http_endpoint('/generate-pdf/:jobcardid', methods=["GET"])
def generate_pdf(jobcardid, document=None, **kwargs):
    try:
        # Convert the string from the URL to an integer before passing it
        job_id_int = int(jobcardid)
        canonical_document = normalize_messenger_document_type(document)
        if not canonical_document:
            return anvil.server.HttpResponse(400, f"Unsupported document type: {document}")

        # This will return the anvil.media object directly to the HTTP response
        media_object = downloadDocument(job_id_int, documentType=canonical_document)

        # Delete the temporary PDF file after creating the media object
        if media_object and media_object.name:
            temp_file_path = media_object.name
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
        return media_object
        
    except ValueError:
        return anvil.server.HttpResponse(400, "Invalid JobCard ID format.")
    except Exception as e:
        # Good practice to catch generation errors so the app knows it failed
        return anvil.server.HttpResponse(500, f"PDF Generation failed: {str(e)}")
    
# *************************************************** Keep Uplink Running Section ************************************
anvil.server.wait_forever()
