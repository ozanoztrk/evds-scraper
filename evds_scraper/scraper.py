from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union 
import pandas as pd
import json
import time



@dataclass
class Variable:
    """Structure for variable definition"""
    category: str
    subcategory: str
    item_name: str
    calculation_type: str


        
@dataclass
class ScraperConfig:
    """Configuration for EVDS Scraper"""
    language: str = "english"
    include_explanations: bool = True
    output_format: str = "excel"
    variables: Optional[List[Variable]] = None
    frequency: Optional[str] = None
    begin_date: Optional[str] = None
    end_date: Optional[str] = None
        
    def is_date_mode_automatic(self) -> bool:
        """Check if we should use automatic date mode"""
        return all([self.frequency is not None, 
                self.begin_date is not None,
                self.end_date is not None])

class EVDSScraper:
    
    FREQUENCIES = {
        'daily': 'Date',
        'workday': 'WORKDAY', 
        'weekly': 'YEARWEEK',
        'monthly': 'MONTH',
        'quarterly': 'QUARTER',
        'semiannual': 'SEMIYEAR',
        'annual': 'YEAR'
    }

    DATE_FORMATS = {
        'Date': 'DD-MM-YYYY',
        'WORKDAY': 'DD-MM-YYYY',
        'YEARWEEK': 'DD-MM-YYYY',
        'MONTH': 'MM-YYYY',
        'QUARTER': 'Q[1-4]-YYYY',
        'SEMIYEAR': 'S[1-2]-YYYY',
        'YEAR': 'YYYY'
    }
    
    def __init__(self, driver, config: Optional[ScraperConfig] = None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.config = config or ScraperConfig()
        self.selected_variables = []
        self.initialize_session()

    def safe_click(self, element):
        """Safely click element"""
        self.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.5)  # Small delay for stability

    def wait_for_element(self, by, value, timeout: int = 5):
        """Wait for element with timeout"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception as e:
            return None

    def wait_for_elements(self, by, value, timeout: int = 5):
        """Wait for elements with timeout"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
        except Exception as e:
            return []

    def get_user_choice(self, max_value: int, start_from_one: bool = True) -> int:
        """Get validated user choice"""
        base = 1 if start_from_one else 0
        while True:
            try:
                choice = int(input("\nSelect number: "))
                if base <= choice <= (max_value - 1 + base):
                    return choice
                print(f"Please enter a number between {base} and {max_value - 1 + base}")
            except ValueError:
                print("Please enter a valid number")
    
    def initialize_session(self):
        """Initialize session and set language"""
        self.driver.get('https://evds2.tcmb.gov.tr/index.php?/evds/serieMarket')
        time.sleep(2)

        lang_button = self.wait_for_element(By.ID, "languageBut")
        current_lang = lang_button.text.strip()
        
        if (self.config.language.lower() == "english" and current_lang == "EN") or \
        (self.config.language.lower() == "turkish" and current_lang == "TR"):
            self.safe_click(lang_button)
            time.sleep(2)


    def _get_elements(self, selector: str, parent_element: WebElement = None, timeout = 5) -> List[WebElement]:
        """Helper method to fetch elements using a CSS selector"""
        try:
            if parent_element:
                return parent_element.find_elements(By.CSS_SELECTOR, selector)
            return self.wait_for_elements(By.CSS_SELECTOR, selector, timeout)
        except Exception as e:
            print(f"Error fetching elements with selector {selector}: {e}")
            return []

    def _select_base(self, 
                    selector_value: Union[str, int], 
                    elements: List[Union[WebElement, Dict]], 
                    get_text_fn: Callable,
                    click_fn: Callable) -> Optional[str]:
        """Generic base method for all selections"""
        try:
            selected = None
            if isinstance(selector_value, str):
                
                # Try exact match first
                for element in elements:
                    text = get_text_fn(element)
                    if selector_value == text:
                        selected = element
                        break

                # If no exact match, try contained match
                if not selected:
                    for element in elements:
                        text = get_text_fn(element)
                        if selector_value in text or text in selector_value:
                            selected = element
                            break

            elif 1 <= selector_value <= len(elements):
                selected = elements[selector_value - 1]

            if not selected:
                print(f"Selection not found: '{selector_value}'")
                return None

            return click_fn(selected)
        except Exception as e:
            print(f"Error in selection: {e}")
            return None
        
    def _select_category_base(self, category_selector: Union[str, int], categories: List[WebElement]) -> Optional[str]:
        """Base method for category selection"""
        def get_text(element: WebElement) -> str:
            return element.text

        def handle_click(element: WebElement) -> str:
            category_code = element.get_attribute('categorycode')
            panel = self.driver.find_element(By.CSS_SELECTOR, f"#collapse_{category_code}")
            is_expanded = panel.get_attribute("class").find("in") != -1

            if not is_expanded:
                self.safe_click(element)
                self.wait.until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, f"#collapse_{category_code}"))
                )
            return element.text

        return self._select_base(category_selector, categories, get_text, handle_click)

    def _select_subcategory_base(self, subcategory_selector: Union[str, int], subcategories: List[Dict]) -> Optional[str]:
        """Base method for subcategory selection"""
        def get_text(element: Dict) -> str:
            return element['text']

        def handle_click(element: Dict) -> str:
            self.safe_click(element['element'])
            return element['text']

        return self._select_base(subcategory_selector, subcategories, get_text, handle_click)

    def _select_item_base(self, item_selector: Union[str, int], items: List[Dict]) -> Optional[str]:
        """Base method for item selection"""
        def get_text(element: Dict) -> str:
            return element['text']

        def handle_click(element: Dict) -> str:
            self.safe_click(element['checkbox'])
            return element['text']

        return self._select_base(item_selector, items, get_text, handle_click)

    def _select_calculation_type_base(self, calc_type_selector: Union[str, int], calc_types: List[Dict]) -> Optional[str]:
        """Base method for calculation type selection"""
        def get_text(element: Dict) -> str:
            return element['text']

        def handle_click(element: Dict) -> str:
            self.safe_click(element['checkbox'])
            self.safe_click(self.driver.find_element(By.TAG_NAME, "body"))  # Close dropdown
            return element['text']

        return self._select_base(calc_type_selector, calc_types, get_text, handle_click)

    def _get_valid_subcategories(self) -> List[Dict]:
        """Helper method to get valid subcategories"""
        subcategories = self._get_elements("a.serieMarketDataGroupItemLink")
        return [{'text': subcat.text.strip(), 'element': subcat} 
                for subcat in subcategories 
                if subcat.text.strip()]

    def _get_valid_items(self) -> List[Dict]:
        """Helper method to get valid items"""
        # Clear previous selections
        checked_items = self._get_elements("input.checkboxes:checked")
        for item in checked_items:
            self.safe_click(item)

        items = []
        rows = self._get_elements("tr.fcsable",None,0.1)
        for row in rows:
            try:
                checkbox = row.find_element(By.CSS_SELECTOR, "input.checkboxes")
                text_cell = row.find_element(By.CSS_SELECTOR, "td.ws_enabled")
                items.append({
                    'text': text_cell.text,
                    'checkbox': checkbox
                })
            except:
                continue
        return items

    def _get_valid_calc_types(self) -> List[Dict]:
        """Helper method to get valid calculation types"""
        # Open dropdown
        dropdown = self.wait_for_element(By.CSS_SELECTOR, "button.multiselect.dropdown-toggle")
        self.safe_click(dropdown)

        # Clear previous selections
        checked = self._get_elements("ul.multiselect-container li.active input[type='checkbox']")
        for item in checked:
            self.safe_click(item)

        calc_types = []
        type_elements = self._get_elements("ul.multiselect-container li")
        for calc_type in type_elements:
            label = calc_type.find_element(By.CSS_SELECTOR, "label.checkbox")
            checkbox = calc_type.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            calc_types.append({
                'text': label.text,
                'checkbox': checkbox
            })
        return calc_types

    def select_category(self) -> Optional[str]:
        """Interactive category selection"""
        try:
            categories = self._get_elements("h4.panel-title.serie-market-menu-category a.accordion-toggle")
            print("\nAvailable Categories:")
            for i, category in enumerate(categories, 1):
                print(f"{i}. {category.text}")

            choice = self.get_user_choice(len(categories))
            return self._select_category_base(choice, categories)
        except Exception as e:
            print(f"Error in interactive category selection: {e}")
            return None

    def select_subcategory(self) -> Optional[str]:
        """Interactive subcategory selection"""
        try:
            subcategories = self._get_valid_subcategories()
            print("\nAvailable Subcategories:")
            for i, subcat in enumerate(subcategories, 1):
                print(f"{i}. {subcat['text']}")

            choice = self.get_user_choice(len(subcategories))
            return self._select_subcategory_base(choice, subcategories)
        except Exception as e:
            print(f"Error in interactive subcategory selection: {e}")
            return None

    def select_item(self) -> Optional[str]:
        """Interactive item selection"""
        try:
            items = self._get_valid_items()
            print("\nAvailable Items:")
            for i, item in enumerate(items, 1):
                print(f"{i}. {item['text']}")

            choice = self.get_user_choice(len(items))
            return self._select_item_base(choice, items)
        except Exception as e:
            print(f"Error in interactive item selection: {e}")
            return None

    def select_calculation_type(self) -> Optional[str]:
        """Interactive calculation type selection"""
        try:
            calc_types = self._get_valid_calc_types()
            print("\nAvailable Calculation Types:")
            for i, calc_type in enumerate(calc_types, 1):
                print(f"{i}. {calc_type['text']}")

            choice = self.get_user_choice(len(calc_types))
            return self._select_calculation_type_base(choice, calc_types)
        except Exception as e:
            print(f"Error in interactive calculation type selection: {e}")
            return None
    
    def add_to_cart(self):
        """Add current selection to cart"""
        add_button = self.wait_for_element(By.CSS_SELECTOR, "a[href*='addToCart']")
        self.safe_click(add_button)
        time.sleep(1)
    
    def create_report(self):
        """Create report"""
        report_button = self.wait_for_element(By.CLASS_NAME, "serieMarketReportButton")
        self.safe_click(report_button)
        time.sleep(2)
    
    def _get_category_elements(self) -> List[WebElement]:
        """Get category elements"""
        return self._get_elements("h4.panel-title.serie-market-menu-category a.accordion-toggle")

    def process_single_variable(self, variable: Variable) -> bool:
        """Process a single variable with error handling"""
        try:
            print(f"Category: '{variable.category}'")
            print(f"Subcategory: '{variable.subcategory}'")
            print(f"Item: '{variable.item_name}'")
            print(f"Calculation type: '{variable.calculation_type}'")

            # Step 1: Select Category
            categories = self._get_category_elements()
            if not categories:
                print("Failed to get categories")
                return False

            if not self._select_category_base(variable.category, categories):
                print(f"Failed to select category: '{variable.category}'")
                return False
            time.sleep(1)  # Wait for subcategories to load

            # Step 2: Select Subcategory
            subcategories = self._get_valid_subcategories()
            if not subcategories:
                print("Failed to get subcategories")
                return False

            if not self._select_subcategory_base(variable.subcategory, subcategories):
                print(f"Failed to select subcategory: '{variable.subcategory}'")
                return False
            time.sleep(2)  # Increased wait time for items to load

            # Step 3: Select Item
            items = self._get_valid_items()
            if not items:
                print("Failed to get items. Available items:")
                rows = self._get_elements("tr.fcsable")
                for row in rows:
                    try:
                        text_cell = row.find_element(By.CSS_SELECTOR, "td.ws_enabled")
                        print(f"- {text_cell.text}")
                    except:
                        continue
                return False

            if not self._select_item_base(variable.item_name, items):
                print(f"Failed to select item: '{variable.item_name}'")
                return False
            time.sleep(1)  # Wait for calculation types to load

            # Step 4: Select Calculation Type
            calc_types = self._get_valid_calc_types()
            if not calc_types:
                print("Failed to get calculation types")
                return False

            if not self._select_calculation_type_base(variable.calculation_type, calc_types):
                print(f"Failed to select calculation type: '{variable.calculation_type}'")
                return False

            self.add_to_cart()
            return True

        except Exception as e:
            print(f"Error processing variable {variable.item_name}: {e}")
            return False
        
    def process_variables_automatically(self) -> bool:
        """Process list of predefined variables"""
        if not self.config.variables:
            return False

        success_count = 0
        total_vars = len(self.config.variables)
        
        for i, variable in enumerate(self.config.variables, 1):
            print(f"\nProcessing variable {i}/{total_vars}")
            if self.process_single_variable(variable):
                success_count += 1
                print(f"Successfully processed {variable.item_name}")
            else:
                print(f"Failed to process {variable.item_name}")
        
        print(f"\nProcessed {success_count}/{total_vars} variables successfully")
        return success_count > 0

    def scrape(self) -> Union[str, Dict, pd.DataFrame]:
        """Main scraping process with automatic or interactive mode"""
        try:          
            var = []  # Initialize var list 
            
            if not self.wait_for_element(By.CSS_SELECTOR,"h4.panel-title.serie-market-menu-category"):
                raise Exception("Page failed to load")
            
            if self.config.variables:
                # Automatic mode
                if not self.process_variables_automatically():
                    raise Exception("Failed to process variables automatically")

            else:
                # Interactive mode
                while True:
                    category = self.select_category()
                    subcategory = self.select_subcategory()
                    item = self.select_item()
                    calculation_type = self.select_calculation_type()
                    self.add_to_cart()
                    var.append([category, subcategory, item, calculation_type])
                    if input("\nAdd more variables? (y/n): ").lower().strip() != 'y':
                        break

                # Store selected variables
                print(f"Used variables are: {var}")
                self.selected_variables = var

            # Create report and process output
            frequency = self.select_frequency()
            begin_date, end_date = self.set_dates()

            # Create and process report
            self.create_report()
            
            # Process output based on format
            if self.config.output_format.lower() == "excel":
                return self.save_as_excel()
            else:                
                table_data = self.parse_table(begin_date)
                explanations = self.parse_explanations() if self.config.include_explanations else None            
            
                if self.config.output_format.lower() in ["df","dataframe"]:
                    df = pd.DataFrame(table_data)
                    if explanations and self.config.include_explanations:
                        df.attrs['explanations'] = explanations
                    return df
                else:  # dict
                    result = {
                        "data": table_data["data"],
                        "columns": table_data["columns"]}
                    if explanations:
                        result["explanations"] = explanations
                    return result

        except Exception as e:
            print(f"Error during scraping: {e}")
            raise
    
    def select_frequency(self) -> str:
        """Select frequency based on config or interactive"""
        try:
            frequency_select = self.wait_for_element(By.ID, "frekansSelect")
            options = frequency_select.find_elements(By.TAG_NAME, "option")

            if self.config.frequency:
                # Automatic mode
                freq_value = self.FREQUENCIES.get(self.config.frequency.lower())
                if not freq_value:
                    available_freqs = ", ".join(self.FREQUENCIES.keys())
                    raise ValueError(f"Invalid frequency '{self.config.frequency}'. Available options are: {available_freqs}")

                # Check if frequency exists in dropdown
                available_values = [opt.get_attribute('value') for opt in options]
                if freq_value not in available_values:
                    raise ValueError(f"Frequency '{freq_value}' not available in dropdown. Available values: {', '.join(available_values)}")

                for option in options:
                    if option.get_attribute('value') == freq_value:
                        self.driver.execute_script(
                            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
                            frequency_select, freq_value
                        )
                        print(f"\nSelected frequency: {option.text}")
                        time.sleep(1)
                        return option.text

            # Interactive mode
            print("\nAvailable Frequencies:")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt.text} ({opt.get_attribute('value')})")

            choice = self.get_user_choice(len(options))
            selected = options[choice - 1]
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
                frequency_select, selected.get_attribute('value')
            )
            print(f"\nSelected frequency: {selected.text}")
            time.sleep(1)
            return selected.text

        except Exception as e:
            print(f"Error selecting frequency: {e}")
            raise

    def get_date_format_by_frequency(self, frequency: str) -> str:
        """Get the required date format based on frequency"""
        format_example = self.DATE_FORMATS.get(frequency, "MM-YYYY")
        print(f"\nRequired date format: {format_example}")
        return format_example
    
    def get_available_dates(self) -> tuple:
        """Get the available date range from labels"""
        try:
            begin_label = self.wait_for_element(By.ID, "beginDateLabel")
            end_label = self.wait_for_element(By.ID, "endDateLabel")

            begin_date = begin_label.text.strip("()")
            end_date = end_label.text.strip("()")

            print(f"\nData available from {begin_date} to {end_date}")
            return begin_date, end_date
        except Exception as e:
            print(f"Error getting available dates: {e}")
            return None, None

    def clear_input_field(self, element):
        """Clear input field properly"""
        try:
            self.safe_click(element)
            element.send_keys(Keys.CONTROL + "a")  # Select all
            element.send_keys(Keys.DELETE)  # Delete selection
            time.sleep(0.5)  # Wait for field to clear
        except Exception as e:
            print(f"Error clearing field: {e}")

    def set_dates(self) -> tuple:
        """Set date range with validation"""
        try:
            # Get current frequency for format validation
            freq_select = self.wait_for_element(By.ID, "frekansSelect")
            current_frequency = freq_select.get_attribute("value")
            
            if self.config.is_date_mode_automatic():
                begin_date = self.config.begin_date
                end_date = self.config.end_date
                print(f"\nUsing configured dates: {begin_date} to {end_date}")
            else:
                # Get available date range
                available_begin, available_end = self.get_available_dates()

                date_format = self.get_date_format_by_frequency(current_frequency)
                print(f"\nEnter dates in format: {date_format}")
                begin_date = input("Begin date: ").strip()
                end_date = input("End date: ").strip()

            # Set begin date
            begin_elem = self.wait_for_element(By.ID, "beginDate")
            self.clear_input_field(begin_elem)
            begin_elem.send_keys(begin_date)
            time.sleep(0.5)

            # Set end date
            end_elem = self.wait_for_element(By.ID, "endDate")
            self.clear_input_field(end_elem)
            end_elem.send_keys(end_date)
            time.sleep(0.5)

            return begin_date, end_date

        except Exception as e:
            print(f"Error setting dates: {e}")
            raise  # Raise error as date setting is critical

    def parse_table(self, begin_date: str) -> Dict[str, Any]:
        """
        Parse the data table by scrolling until beginning date is found
        Args:
            begin_date: The target beginning date to scroll to
        """
        try:
            # Prepare alternative date format if there's only one hyphen
            alternative_date = None
            if begin_date.count('-') == 1:
                # Split and swap parts around the hyphen
                month, year = begin_date.split('-')
                alternative_date = f"{year}-{month}"


            # Wait for table content to load
            self.wait_for_element(By.CLASS_NAME, "dx-datagrid-content")

            # Get headers
            headers = self.wait_for_elements(
                By.CSS_SELECTOR, 
                "td[role='columnheader'] .dx-datagrid-text-content"
            )
            column_names = [header.text.strip() for header in headers]

            # Find scroll container
            scroll_container = self.wait_for_element(
                By.CSS_SELECTOR, 
                "div.dx-scrollable-container"
            )

            processed_rows = set()
            data = []
            found_begin_date = False

            while not found_begin_date:
                # Get current visible rows
                rows = self.wait_for_elements(
                    By.CSS_SELECTOR, 
                    "tr.dx-row.dx-data-row"
                )

                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if not cells:
                            continue

                        row_date = cells[0].text.strip()

                        if row_date and row_date not in processed_rows:
                            if len(cells) >= len(column_names):
                                row_data = {}
                                for idx, cell in enumerate(cells):
                                    if idx < len(column_names):
                                        row_data[column_names[idx]] = cell.text.strip()
                                data.append(row_data)


                                # Check both date formats
                                if row_date == begin_date or (alternative_date and row_date == alternative_date):
                                    print(f"Found matching date: {row_date}")
                                    found_begin_date = True
                                    break

                    except Exception as e:
                        print(f"Error parsing row: {e}")
                        continue

                if not found_begin_date:
                    self.driver.execute_script(
                        "arguments[0].scrollTop += 100",
                        scroll_container
                    )
                    time.sleep(0.5)

            print(f"\nParsed {len(data)} rows with {len(column_names)} columns")
            return data

        except Exception as e:
            print(f"Error parsing table: {e}")
            return {"columns": [], "data": [], "row_count": 0}

    def parse_explanations(self) -> List[Dict[str, str]]:
        """Parse the explanation section with improved error handling"""
        try:
            # Wait for explanation tab
            self.wait_for_element(By.ID, "tab_6_1_")
            time.sleep(1)  # Wait for content to load

            # Get all variable sections
            var_sections = self.wait_for_elements(
                By.CSS_SELECTOR,
                "#tab_6_1_ .col-md-12"
            )

            explanations = []
            for section in var_sections:
                try:
                    # Get code
                    code_elem = section.find_element(
                        By.CSS_SELECTOR,
                        ".col-md-4 h6 p"
                    )
                    code = code_elem.text.strip()

                    # Get description and calculation type
                    desc_container = section.find_element(
                        By.CSS_SELECTOR,
                        ".col-md-4:nth-child(2) h6"
                    )
                    desc_elem = desc_container.find_element(By.CSS_SELECTOR, "p")
                    desc_text = desc_elem.text.strip()
                    
                    # Get additional info
                    info_div = desc_container.find_element(By.CSS_SELECTOR, "div[id^='infoD_']")
                    additional_info = info_div.text.strip()

                    # Split description into parts
                    desc_parts = desc_text.split("-")
                    main_desc = desc_parts[0].strip()
                    calc_type = desc_parts[-1].strip() if len(desc_parts) > 1 else ""

                    # Create explanation entry
                    explanation = {
                        "code": code,
                        "description": main_desc,
                        "calculation_type": calc_type.strip("<i>").strip("</i>"),
                        "additional_info": additional_info
                    }
                    explanations.append(explanation)

                except Exception as e:
                    print(f"Error parsing explanation section: {e}")
                    continue

            print(f"\nParsed {len(explanations)} variable explanations")
            return explanations

        except Exception as e:
            print(f"Error parsing explanations: {e}")
            return []

    def save_as_excel(self) -> bool:
        """Export data to Excel"""
        try:
            # Find and click Excel button
            excel_button = self.wait_for_element(
                By.CSS_SELECTOR,
                "div#excelButton_"
            )
            self.safe_click(excel_button)
            time.sleep(1)

            # Find and click download button
            download_button = self.wait_for_element(
                By.ID, 
                "evdsDscModalButtonDownload"
            )
            self.safe_click(download_button)
            time.sleep(2)  # Wait for download to start

            print("\nExcel export completed")
            return True

        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return False

    
    def export_configuration(self, filepath: str) -> bool:
        """
        Export current configuration and selected variables to a JSON file

        Args:
            filepath (str): Path where the configuration file will be saved
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            # Add .json extension if missing
            if not filepath.endswith('.json'):
                filepath += '.json'

            # Create basic config dictionary
            config_dict = {
                "language": self.config.language,
                "variables": []
            }

            # Add selected variables
            for var in self.selected_variables:
                if isinstance(var, list) and len(var) == 4:
                    config_dict["variables"].append({
                        "category": var[0],
                        "subcategory": var[1],
                        "item_name": var[2],
                        "calculation_type": var[3]
                    })

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=2)

            print(f"Configuration saved to: {filepath}")
            return True

        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False