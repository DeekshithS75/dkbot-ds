import gspread
from google.oauth2.service_account import Credentials
import logging
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GoogleSheetsClient:
    def __init__(self):
        self.worksheets = self._get_sheets()
        self.sheet = self.worksheets['individual']
        self._ensure_columns('individual')
        self._ensure_columns('college')

    def _get_sheets(self):
        """Connects to Google Sheets and returns worksheet objects for individual and college applicants."""
        try:
            if not config.GOOGLE_SERVICE_ACCOUNT_EMAIL or not config.GOOGLE_PRIVATE_KEY:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_EMAIL and GOOGLE_PRIVATE_KEY must be set in .env")

            creds_json = {
                "type": "service_account",
                "client_email": config.GOOGLE_SERVICE_ACCOUNT_EMAIL,
                "private_key": config.GOOGLE_PRIVATE_KEY.replace('\n', '\n'),
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            creds = Credentials.from_service_account_info(creds_json, scopes=config.SHEETS_SCOPES)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_url(config.GOOGLE_SHEET_URL)
            
            individual_sheet = spreadsheet.get_worksheet(0)
            college_sheet = spreadsheet.get_worksheet(1)
            
            logging.info("✅ Successfully connected to both Google Sheets worksheets.")
            return {'individual': individual_sheet, 'college': college_sheet}
        except Exception as e:
            logging.error(f"❌ Failed to connect to Google Sheets: {e}")
            raise

    def _ensure_columns(self, applicant_type: str):
        """Ensures that the necessary columns exist in the given sheet, adding them if they don't."""
        worksheet = self.worksheets[applicant_type]
        try:
            headers = worksheet.row_values(1)
            
            if applicant_type == 'individual':
                required_cols = [
                    config.COL_RESPONDED, 
                    config.COL_ROLE_CLAIMED,
                ]
            elif applicant_type == 'college':
                required_cols = [
                    config.COL_RESPONDED,
                ]
            else:
                required_cols = []

            first_empty_col = len(headers) + 1
            
            for col in required_cols:
                if col not in headers:
                    worksheet.update_cell(1, first_empty_col, col)
                    logging.info(f"Added missing column '{col}' to sheet '{worksheet.title}'.")
                    headers.append(col)
                    first_empty_col += 1
        except Exception as e:
            logging.error(f"Failed to ensure columns in sheet '{worksheet.title}': {e}")

    def add_individual_applicant(self, data: dict):
        """Appends a new row with individual applicant data to the individual sheet."""
        try:
            worksheet = self.worksheets['individual']
            headers = worksheet.row_values(1)
            
            new_row = [data.get(header, "") for header in headers]
            
            worksheet.append_row(new_row, value_input_option='USER_ENTERED')
            logging.info(f"Successfully added individual applicant: {data.get(config.COL_EMAIL)}")
            return True
        except Exception as e:
            logging.error(f"Failed to add individual applicant to sheet: {e}")
            return False

    def add_college_applicant(self, data: dict):
        """Appends a new row with college applicant data to the college sheet."""
        try:
            worksheet = self.worksheets['college']
            headers = worksheet.row_values(1)
            
            new_row = [data.get(header, "") for header in headers]
            
            worksheet.append_row(new_row, value_input_option='USER_ENTERED')
            logging.info(f"Successfully added college applicant: {data.get(config.COL_COLLEGE_NAME)}")
            return True
        except Exception as e:
            logging.error(f"Failed to add college applicant to sheet: {e}")
            return False

    # --- Methods below this line operate on the default 'individual' sheet ---

    def get_all_records(self):
        """Returns all records from the individual sheet."""
        try:
            return self.sheet.get_all_records()
        except Exception as e:
            logging.error(f"Failed to get all records: {e}")
            return []

    def find_cell(self, query: str):
        """Finds a cell matching the query in the individual sheet."""
        try:
            return self.sheet.find(query)
        except gspread.exceptions.CellNotFound:
            return None
        except Exception as e:
            logging.error(f"Error finding cell for query '{query}': {e}")
            return None

    def get_row(self, row_index: int):
        """Gets a specific row by its index from the individual sheet."""
        try:
            return self.sheet.row_values(row_index)
        except Exception as e:
            logging.error(f"Error getting row {row_index}: {e}")
            return None

    def update_cell(self, row: int, col: int, value: str):
        """Updates a single cell in the individual sheet."""
        try:
            self.sheet.update_cell(row, col, value)
            return True
        except Exception as e:
            logging.error(f"Failed to update cell ({row}, {col}): {e}")
            return False

    def get_record_by_email(self, email: str):
        """Finds a user record by their email address in the individual sheet."""
        cell = self.find_cell(email)
        if not cell:
            return None
        
        row_data = self.get_row(cell.row)
        headers = self.sheet.row_values(1)
        return dict(zip(headers, row_data))

    def update_status_by_email(self, email: str, status: str) -> bool:
        """
        Updates the 'accepted' and 'responded' status for a user by email in the individual sheet.
        'status' should be 'yes' or 'no'.
        """
        logging.info(f"Updating status for {email} to '{status}'")
        try:
            cell = self.find_cell(email)
            if not cell:
                logging.warning(f"Could not find user with email {email} to update status.")
                return False
            
            headers = self.sheet.row_values(1)
            accepted_col_index = headers.index(config.COL_ACCEPTED) + 1
            responded_col_index = headers.index(config.COL_RESPONDED) + 1
            
            self.sheet.update_cell(cell.row, accepted_col_index, status)
            self.sheet.update_cell(cell.row, responded_col_index, "yes")
            logging.info(f"Successfully updated status for {email}.")
            return True
        except (ValueError, gspread.exceptions.CellNotFound) as e:
            logging.error(f"Column not found or cell not found for {email}: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred while updating status for {email}: {e}")
            return False

    def claim_role_by_email(self, email: str) -> bool:
        """Updates the 'roleClaimed' status for a user by email in the individual sheet."""
        logging.info(f"Updating role claimed status for {email}")
        try:
            cell = self.find_cell(email)
            if not cell:
                logging.warning(f"Could not find user with email {email} to update role status.")
                return False
            
            headers = self.sheet.row_values(1)
            claimed_col_index = headers.index(config.COL_ROLE_CLAIMED) + 1
            
            self.sheet.update_cell(cell.row, claimed_col_index, "yes")
            logging.info(f"Successfully updated role claimed status for {email}.")
            return True
        except (ValueError, gspread.exceptions.CellNotFound) as e:
            logging.error(f"Column not found or cell not found for {email}: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred while updating role status for {email}: {e}")
            return False

    def get_records_by_status(self, status: str):
        """
        Returns records filtered by the 'accepted' column from the individual sheet.
        'status' can be 'approved', 'rejected', or 'pending'.
        """
        try:
            all_records = self.get_all_records()
            results = []
            for record in all_records:
                record_status = str(record.get(config.COL_ACCEPTED, "")).strip().lower()
                if status == 'approved' and record_status == 'yes':
                    results.append(record)
                elif status == 'rejected' and record_status == 'no':
                    results.append(record)
                elif status == 'pending' and record_status not in ['yes', 'no']:
                    results.append(record)
            return results
        except Exception as e:
            logging.error(f"Could not retrieve records by status '{status}': {e}")
            return []

    def search_records(self, query: str):
        """Searches for records where the query matches part of the name or email in the individual sheet."""
        try:
            all_records = self.get_all_records()
            query = query.lower()
            results = []
            for record in all_records:
                name = f"{record.get(config.COL_FIRST_NAME, '')} {record.get(config.COL_LAST_NAME, '')}".lower()
                email = str(record.get(config.COL_EMAIL, '')).lower()
                if query in name or query in email:
                    results.append(record)
            return results
        except Exception as e:
            logging.error(f"An error occurred during search: {e}")
            return []

    def get_stats(self):
        """Returns a dictionary with counts of accepted, rejected, and pending applicants from the individual sheet."""
        stats = {'approved': 0, 'rejected': 0, 'pending': 0, 'total': 0}
        try:
            records = self.get_all_records()
            for record in records:
                stats['total'] += 1
                status = str(record.get(config.COL_ACCEPTED, "")).strip().lower()
                if status == 'yes':
                    stats['approved'] += 1
                elif status == 'no':
                    stats['rejected'] += 1
                else:
                    stats['pending'] += 1
            return stats
        except Exception as e:
            logging.error(f"Could not retrieve stats from sheet: {e}")
            return stats
