import gspread
from google.oauth2.service_account import Credentials
import logging
import config
import random
import string

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_random_id(length=6):
    """Generates a random alphanumeric ID of a given length."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class GoogleSheetsClient:
    def __init__(self):
        self.worksheets = self._get_sheets()
        self.sheet = self.worksheets['individual']
        self._ensure_columns('individual')
        self._ensure_columns('college')

    def _get_sheets(self):
        """Connects to Google Sheets and returns worksheet objects for all required sheets."""
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
            events_submission_sheet = spreadsheet.get_worksheet(2)
            events_accepted_sheet = spreadsheet.get_worksheet(3)
            events_rejected_sheet = spreadsheet.get_worksheet(4)
            
            logging.info("✅ Successfully connected to all Google Sheets worksheets.")
            return {
                'individual': individual_sheet, 
                'college': college_sheet,
                'events_submission': events_submission_sheet,
                'events_accepted': events_accepted_sheet,
                'events_rejected': events_rejected_sheet
            }
        except Exception as e:
            logging.error(f"❌ Failed to connect to Google Sheets: {e}")
            raise

    def _ensure_columns(self, applicant_type: str):
        """Ensures that the necessary columns exist in the given sheet, adding them if they don't."""
        if applicant_type not in self.worksheets:
            logging.warning(f"Worksheet for '{applicant_type}' not found. Skipping column check.")
            return
            
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

            if not required_cols:
                return

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

    def add_event_submission(self, data: dict) -> str:
        """Appends a new row with event data to the Events Submission sheet and returns the event ID."""
        try:
            worksheet = self.worksheets['events_submission']
            headers = worksheet.row_values(1)
            event_id = generate_random_id()
            data['ID'] = event_id
            
            new_row = [str(data.get(header, "")) for header in headers]

            worksheet.append_row(new_row, value_input_option='USER_ENTERED')
            logging.info(f"Successfully added event submission with ID: {event_id}")
            return event_id
        except Exception as e:
            logging.error(f"Failed to add event submission to sheet: {e}")
            return None

    def _find_row_by_id(self, worksheet, event_id: str):
        """Finds a row in a worksheet by the event ID."""
        try:
            id_column_index = worksheet.row_values(1).index("ID") + 1
            cell = worksheet.find(event_id, in_column=id_column_index)
            return cell.row, worksheet.row_values(cell.row)
        # except (gspread.exceptions.CellNotFound, ValueError):
        #     logging.warning(f"Could not find event with ID '{event_id}' in sheet '{worksheet.title}'.")
        #     return None, None
        except Exception as e:
            logging.error(f"Error finding event ID '{event_id}' in sheet '{worksheet.title}': {e}")
            return None, None

    def _move_event(self, source_sheet_name: str, dest_sheet_name: str, event_id: str) -> bool:
        """Moves an event row from a source sheet to a destination sheet."""
        try:
            source_sheet = self.worksheets[source_sheet_name]
            dest_sheet = self.worksheets[dest_sheet_name]

            row_index, row_data = self._find_row_by_id(source_sheet, event_id)
            if row_index and row_data:
                dest_sheet.append_row(row_data, value_input_option='USER_ENTERED')
                source_sheet.delete_rows(row_index)
                logging.info(f"Moved event '{event_id}' from '{source_sheet.title}' to '{dest_sheet.title}'.")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to move event '{event_id}': {e}")
            return False

    def accept_event_submission(self, event_id: str) -> bool:
        """Moves an event from the submission sheet to the accepted sheet."""
        return self._move_event('events_submission', 'events_accepted', event_id)

    def reject_event_submission(self, event_id: str) -> bool:
        """Moves an event from the submission sheet to the rejected sheet."""
        return self._move_event('events_submission', 'events_rejected', event_id)

    def revert_rejection(self, event_id: str) -> bool:
        """Moves an event from the rejected sheet back to the submission sheet."""
        return self._move_event('events_rejected', 'events_submission', event_id)

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
        # except gspread.exceptions.CellNotFound:
        #     return None
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
        # except (ValueError, gspread.exceptions.CellNotFound) as e:
        #     logging.error(f"Column not found or cell not found for {email}: {e}")
        #     return False
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
        # except (ValueError, gspread.exceptions.CellNotFound) as e:
        #     logging.error(f"Column not found or cell not found for {email}: {e}")
        #     return False
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
