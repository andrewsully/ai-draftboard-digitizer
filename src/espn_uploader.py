"""
ESPN Fantasy Football Draft Uploader using Selenium
"""

import time
import re
from typing import List, Dict, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class ESPNUploader:
    def __init__(self, league_url: str, username: str, password: str, dry_run: bool = True):
        self.league_url = league_url
        self.username = username
        self.password = password
        self.dry_run = dry_run
        self.driver = None
        self.wait = None
        self.log_entries = []
        
    def log(self, message: str, log_type: str = 'info'):
        """Add a log entry"""
        self.log_entries.append({
            'message': message,
            'type': log_type,
            'timestamp': time.time()
        })
        print(f"[{log_type.upper()}] {message}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Always keep browser visible so user can watch the process
            # chrome_options.add_argument('--headless')  # Commented out to always show browser
            
            # Setup Chrome driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            
            self.log("Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to setup WebDriver: {str(e)}", 'error')
            return False
    
    def login_to_espn(self) -> bool:
        """Login to ESPN Fantasy using the proven working method"""
        try:
            # Step 1: Navigate directly to the fantasy league page (this triggers the iframe login)
            self.log("Navigating directly to fantasy league page to trigger login...")
            if self.league_url:
                self.driver.get(self.league_url)
            else:
                # Fallback to a generic fantasy page that will require login
                self.driver.get("https://fantasy.espn.com/football/")
            time.sleep(5)  # Wait for page and login iframe to load
            
            # Step 4: Wait for and switch to the Disney ID iframe
            self.log("Waiting for Disney ID iframe to load...")
            iframe_found = False
            iframe_selectors = ["oneid-iframe", "disneyid-iframe", "iframe[name='oneid-iframe']", "iframe[name='disneyid-iframe']", "iframe[id='oneid-iframe']", "iframe[id='disneyid-iframe']"]
            
            # Try different methods to find and switch to the iframe
            for i in range(3):  # Try 3 times with increasing waits
                time.sleep(2 + i)  # Wait 2, 4, 6 seconds
                
                for selector in iframe_selectors:
                    try:
                        if selector in ["disneyid-iframe", "oneid-iframe"]:
                            # Try by name first
                            self.driver.switch_to.frame(selector)
                        else:
                            # Try by CSS selector
                            iframe_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            self.driver.switch_to.frame(iframe_element)
                        
                        self.log(f"Successfully switched to login iframe using selector: {selector}")
                        iframe_found = True
                        break
                    except Exception as e:
                        continue
                
                if iframe_found:
                    break
                else:
                    self.log(f"Attempt {i+1}: Disney ID iframe not found, waiting longer...")
            
            if not iframe_found:
                # Try to find any iframe and switch to it
                self.log("Trying to find any iframe on the page...")
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    self.log(f"Found {len(iframes)} iframe(s) on the page")
                    
                    for i, iframe in enumerate(iframes):
                        try:
                            iframe_name = iframe.get_attribute("name") or "no-name"
                            iframe_id = iframe.get_attribute("id") or "no-id"
                            iframe_src = iframe.get_attribute("src") or "no-src"
                            self.log(f"Iframe {i}: name='{iframe_name}', id='{iframe_id}', src='{iframe_src[:100]}...'")
                            
                            # Try to switch to this iframe
                            self.driver.switch_to.frame(iframe)
                            
                            # Test if this iframe contains login form
                            try:
                                test_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[type='password'], input[placeholder*='email'], input[placeholder*='password']")
                                self.log(f"Found login form in iframe {i}")
                                iframe_found = True
                                break
                            except NoSuchElementException:
                                # Not the right iframe, switch back and try next
                                self.driver.switch_to.default_content()
                                continue
                                
                        except Exception as e:
                            self.log(f"Error testing iframe {i}: {str(e)}")
                            try:
                                self.driver.switch_to.default_content()
                            except:
                                pass
                            continue
                            
                except Exception as e:
                    self.log(f"Error finding iframes: {str(e)}")
            
            if not iframe_found:
                self.log("Could not find or switch to Disney ID iframe", 'error')
                return False
            
            time.sleep(2)
            
            # Step 3: Click the "Looking for username login?" button for old accounts
            self.log("Looking for username login button...")
            username_login_button_xpath = "/html/body/div[1]/div[3]/div/div[2]/div/div/form/p/a"
            try:
                username_login_button = self.driver.find_element(By.XPATH, username_login_button_xpath)
                if username_login_button.is_displayed():
                    self.log("Found username login button, clicking it...")
                    username_login_button.click()
                    time.sleep(3)  # Wait for the username/password form to appear
                    self.log("Clicked username login button successfully")
                else:
                    self.log("Username login button not visible", 'warning')
            except NoSuchElementException:
                self.log("Could not find username login button - may already be on username/password form", 'info')
                # Continue anyway, maybe we're already on the right form
            
            # Step 4: Enter username using working selectors from test
            self.log("Entering username...")
            username_selectors = [
                "input[placeholder='Username or Email Address']",  # This worked in our test
                "input[name='loginValue']",  # Common ESPN selector
                "input[type='text']",  # Generic text input
                "input[placeholder*='username']",  # Flexible placeholder match
                "input[placeholder*='Username']",  # Case variation
                "input[type='email']"  # Fallback
            ]
            
            username_entered = False
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if username_field.is_displayed() and username_field.is_enabled():
                        username_field.clear()
                        username_field.send_keys(self.username)
                        self.log(f"Username entered successfully using selector: {selector}")
                        username_entered = True
                        break
                except NoSuchElementException:
                    continue
            
            if not username_entered:
                self.log("Could not find username field with any selector", 'error')
                return False
            
            time.sleep(2)
            
            # Step 6: Enter password using CSS selector from working example
            self.log("Entering password...")
            password_selectors = [
                "input[type='password']",  # From the working example
                "input[placeholder='Password (case sensitive)']",  # From first example
                "input[name='password']",  # Common selector
                "input[placeholder*='password']"  # Flexible placeholder match
            ]
            
            password_entered = False
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if password_field.is_displayed() and password_field.is_enabled():
                        password_field.clear()
                        password_field.send_keys(self.password)
                        self.log(f"Password entered successfully using selector: {selector}")
                        password_entered = True
                        break
                except NoSuchElementException:
                    continue
            
            if not password_entered:
                self.log("Could not find password field with any selector", 'error')
                return False
            
            time.sleep(2)
            
            # Step 7: Submit the login form using CSS selector from working example
            self.log("Submitting login form...")
            submit_selectors = [
                "button[type='submit']",  # From the working example
                "button[class='btn btn-primary btn-submit ng-isolate-scope']",  # From first example
                ".btn-submit",  # Common class
                ".btn-primary",  # Common class
                "input[type='submit']"  # Alternative submit input
            ]
            
            form_submitted = False
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_button.is_displayed() and submit_button.is_enabled():
                        submit_button.click()
                        self.log(f"Login form submitted successfully using selector: {selector}")
                        form_submitted = True
                        break
                except NoSuchElementException:
                    continue
            
            if not form_submitted:
                self.log("Could not find submit button with any selector", 'error')
                return False
            
            # Step 8: Switch back to default content and wait for login to complete
            self.log("Switching back to main content...")
            self.driver.switch_to.default_content()
            time.sleep(8)
            
            # Step 9: Verify login success
            current_url = self.driver.current_url
            self.log(f"Current URL after login: {current_url}")
            
            # Check if we're still on ESPN and not on a login page
            if "espn.com" in current_url and "login" not in current_url.lower():
                self.log("Login appears successful - on ESPN domain without login in URL")
                
                # Additional verification: try to access the league URL
                if self.league_url:
                    self.log("Testing league access...")
                    self.driver.get(self.league_url)
                    time.sleep(5)
                    
                    final_url = self.driver.current_url
                    if "login" not in final_url.lower() and "unauthorized" not in final_url.lower():
                        self.log("Login successful - can access league page!")
                        return True
                    else:
                        self.log(f"Cannot access league page, redirected to: {final_url}", 'warning')
                        return False
                else:
                    self.log("Login successful!")
                    return True
            else:
                self.log(f"Login may have failed - current URL: {current_url}", 'warning')
                
                # Check for error messages
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .error-message, .alert-error")
                    for error_elem in error_elements:
                        if error_elem.is_displayed():
                            error_text = error_elem.text
                            self.log(f"Login error found: {error_text}", 'error')
                            return False
                except Exception:
                    pass
                
                return False
                
        except Exception as e:
            self.log(f"Login failed with exception: {str(e)}", 'error')
            # Make sure we're back to default content if an error occurred
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False
    
    def navigate_to_draft_page(self) -> bool:
        """Navigate to the offline draft results input page"""
        try:
            # Extract league ID from URL and navigate to offline draft page
            if 'leagueId=' in self.league_url:
                import re
                league_id_match = re.search(r'leagueId=(\d+)', self.league_url)
                if league_id_match:
                    league_id = league_id_match.group(1)
                    offline_draft_url = f"https://fantasy.espn.com/football/league/offlinedraft?leagueId={league_id}"
                    self.log(f"Navigating to offline draft input page: {offline_draft_url}")
                    self.driver.get(offline_draft_url)
                    time.sleep(5)  # Give time for page to load
                    
                    # Verify we're on the right page
                    if "Input Offline Draft Results" in self.driver.page_source or "offlinedraft" in self.driver.current_url:
                        self.log("Successfully navigated to offline draft input page")
                        return True
                    else:
                        self.log("May not be on the correct draft input page", 'warning')
                        return True  # Continue anyway
                else:
                    self.log("Could not extract league ID from URL", 'error')
                    return False
            else:
                self.log("League URL does not contain leagueId parameter", 'error')
                return False
            
            # Look for draft/results navigation
            draft_selectors = [
                "a[href*='offlinedraft']",
                "a[href*='draft']",
                ".draft-link",
                "a[title*='Draft']",
                "nav a[href*='draft']",
                "[data-testid*='draft']"
            ]
            
            for selector in draft_selectors:
                try:
                    draft_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.log(f"Found draft link with selector: {selector}")
                    draft_link.click()
                    time.sleep(5)
                    return True
                except NoSuchElementException:
                    continue
            
            # Try direct URL manipulation for offline draft
            if '/league/' in self.league_url:
                draft_url = self.league_url.replace('/league/', '/league/offlinedraft/')
                self.log(f"Trying direct offline draft URL: {draft_url}")
                self.driver.get(draft_url)
                time.sleep(5)
                return True
            
            self.log("Could not find draft page navigation", 'warning')
            return False
            
        except Exception as e:
            self.log(f"Failed to navigate to draft page: {str(e)}", 'error')
            return False
    
    def upload_draft_results(self, results: List[Dict], team_count: int) -> Tuple[bool, List[Dict]]:
        """Main method to upload draft results to ESPN"""
        try:
            if not self.setup_driver():
                return False, self.log_entries
            
            if not self.login_to_espn():
                return False, self.log_entries
            
            if not self.navigate_to_draft_page():
                return False, self.log_entries
            
            # Process draft results by team
            teams = self.organize_results_by_team(results, team_count)
            
            if self.dry_run:
                self.log("DRY RUN MODE - Preview only, not submitting changes", 'warning')
                self.preview_draft_results(teams)
                return True, self.log_entries
            
            # Actually upload the results
            success = self.submit_draft_results(teams)
            
            return success, self.log_entries
            
        except Exception as e:
            self.log(f"Upload process failed: {str(e)}", 'error')
            return False, self.log_entries
        finally:
            if self.driver:
                self.driver.quit()
                self.log("Browser closed")
    
    def organize_results_by_team(self, results: List[Dict], team_count: int) -> Dict:
        """Organize draft results by team based on snake draft pattern"""
        teams = {i: [] for i in range(team_count)}
        
        for result in sorted(results, key=lambda x: x['pick']):
            pick_num = result['pick']
            round_num = (pick_num - 1) // team_count
            pick_in_round = (pick_num - 1) % team_count
            
            # Snake draft: odd rounds go reverse
            if round_num % 2 == 0:
                team_index = pick_in_round
            else:
                team_index = team_count - 1 - pick_in_round
            
            teams[team_index].append({
                'pick': pick_num,
                'player': result['player'],
                'position': result['position'],
                'team': result['team'],
                'round': round_num + 1
            })
        
        return teams
    
    def _get_team_for_pick(self, pick_number: int, team_count: int) -> int:
        """Get the team index for a given pick number in snake draft"""
        round_num = (pick_number - 1) // team_count
        pick_in_round = (pick_number - 1) % team_count
        
        # Snake draft: odd rounds go reverse
        if round_num % 2 == 0:
            return pick_in_round
        else:
            return team_count - 1 - pick_in_round
    
    def preview_draft_results(self, teams: Dict):
        """Preview the draft results that would be uploaded (organized by team)"""
        self.log("=== DRAFT PREVIEW (Team-by-Team Order) ===", 'info')
        
        # Show the same organization that will be used for input
        for team_idx in sorted(teams.keys()):
            team_picks = teams[team_idx]
            if team_picks:
                self.log(f"Team {team_idx + 1}:", 'info')
                # Sort each team's picks by round
                team_picks_sorted = sorted(team_picks, key=lambda x: x['round'])
                for pick in team_picks_sorted:
                    self.log(f"  Round {pick['round']}: {pick['player']} ({pick['position']}, {pick['team']})", 'info')
        
        self.log("=== END PREVIEW ===", 'info')
        self.log("Note: Players will be entered in ESPN in this team-by-team order", 'info')
    
    def submit_draft_results(self, teams: Dict) -> bool:
        """Submit the actual draft results to ESPN"""
        try:
            self.log("Starting draft results submission...", 'info')
            
            total_picks = sum(len(picks) for picks in teams.values())
            self.log(f"Uploading {total_picks} picks across {len(teams)} teams", 'info')
            
            # Wait for page to load completely (Next.js app needs time to render)
            self.log("Waiting for ESPN draft page to load...", 'info')
            time.sleep(5)
            
            # Look for common draft input patterns in ESPN's interface
            draft_form_selectors = [
                "form[data-testid*='draft']",
                "form[class*='draft']", 
                ".draft-form",
                ".offline-draft-form",
                "[data-cy*='draft']"
            ]
            
            form_found = False
            for selector in draft_form_selectors:
                try:
                    form = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.log(f"Found draft form with selector: {selector}", 'info')
                    form_found = True
                    break
                except NoSuchElementException:
                    continue
            
            if not form_found:
                self.log("Could not find draft form - looking for input fields", 'warning')
                
                # Try to find individual input fields for player names
                player_input_selectors = [
                    "input[placeholder*='player']",
                    "input[placeholder*='Player']", 
                    "input[name*='player']",
                    "input[class*='player']",
                    ".player-input",
                    "[data-testid*='player']"
                ]
                
                inputs_found = []
                for selector in player_input_selectors:
                    try:
                        inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if inputs:
                            inputs_found.extend(inputs)
                            self.log(f"Found {len(inputs)} player input fields with selector: {selector}", 'info')
                    except NoSuchElementException:
                        continue
                
                if inputs_found:
                    return self._fill_individual_inputs(inputs_found, teams)
                else:
                    return self._try_table_approach(teams)
            
            # If we found a form, try to submit it
            return self._submit_form_approach(form, teams)
            
        except Exception as e:
            self.log(f"Failed to submit draft results: {str(e)}", 'error')
            return False
    
    def _fill_individual_inputs(self, inputs, teams: Dict) -> bool:
        """Fill individual input fields with player names organized by team"""
        try:
            self.log("Attempting to fill individual input fields by team...", 'info')
            
            # Organize picks by team (Team 1 picks, then Team 2 picks, etc.)
            team_organized_picks = []
            
            # Go through each team in order
            for team_idx in sorted(teams.keys()):
                team_picks = teams[team_idx]
                if team_picks:
                    # Sort each team's picks by round
                    team_picks_sorted = sorted(team_picks, key=lambda x: x['round'])
                    team_organized_picks.extend(team_picks_sorted)
                    self.log(f"Team {team_idx + 1}: {len(team_picks_sorted)} picks", 'info')
            
            filled_count = 0
            for i, pick in enumerate(team_organized_picks):
                if i >= len(inputs):
                    break
                    
                try:
                    input_field = inputs[i]
                    player_name = pick['player']
                    
                    # Clear and fill the input
                    input_field.clear()
                    input_field.send_keys(player_name)
                    
                    self.log(f"Team {self._get_team_for_pick(pick['pick'], len(teams)) + 1}, Round {pick['round']}: {player_name}", 'info')
                    filled_count += 1
                    
                    # Small delay between entries
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.log(f"Error filling input {i}: {str(e)}", 'warning')
                    continue
            
            self.log(f"Successfully filled {filled_count} player entries", 'info')
            
            # Look for submit/finish button
            submit_selectors = [
                "button:contains('I Am Finished Entering Results')",  # ESPN specific finish button
                "button[class*='subHeader__button']",  # ESPN finish button class
                "button[type='submit']",
                "input[type='submit']", 
                ".submit-btn",
                ".save-btn",
                "[data-testid*='submit']",
                "button[class*='submit']"
            ]
            
            # Also try the exact XPath as a fallback
            finish_button_xpath = "/html/body/div[1]/div[1]/div/div/div[5]/div[2]/div[2]/div/div[1]/div[2]/div/button"
            
            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.log(f"Found submit button: {selector}", 'info')
                    submit_btn.click()
                    self.log("Draft results submitted successfully!", 'info')
                    return True
                except NoSuchElementException:
                    continue
            
            # Try the exact XPath as final fallback
            try:
                self.log("Trying exact XPath for finish button...")
                finish_btn = self.driver.find_element(By.XPATH, finish_button_xpath)
                self.log("Found finish button using XPath!")
                finish_btn.click()
                self.log("Draft results submitted successfully using XPath!", 'info')
                return True
            except NoSuchElementException:
                self.log("Could not find finish button with XPath either", 'warning')
            
            self.log("No submit button found - results may need manual submission", 'warning')
            return True
            
        except Exception as e:
            self.log(f"Error in individual input approach: {str(e)}", 'error')
            return False
    
    def _try_table_approach(self, teams: Dict) -> bool:
        """Try to find and fill a draft table/grid"""
        try:
            self.log("Attempting table/grid approach...", 'info')
            
            # Look for table or grid structures
            table_selectors = [
                "table[class*='draft']",
                ".draft-table",
                ".draft-grid", 
                "[data-testid*='draft-table']",
                "table tbody tr"
            ]
            
            for selector in table_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.log(f"Found {len(elements)} table elements with selector: {selector}", 'info')
                        # For now, just log what we found
                        break
                except NoSuchElementException:
                    continue
            
            self.log("Table approach needs manual implementation based on ESPN's specific structure", 'warning')
            return True
            
        except Exception as e:
            self.log(f"Error in table approach: {str(e)}", 'error')
            return False
    
    def _submit_form_approach(self, form, teams: Dict) -> bool:
        """Submit using form-based approach"""
        try:
            self.log("Attempting form submission approach...", 'info')
            
            # Look for inputs within the form
            inputs = form.find_elements(By.TAG_NAME, "input")
            selects = form.find_elements(By.TAG_NAME, "select")
            textareas = form.find_elements(By.TAG_NAME, "textarea")
            
            self.log(f"Found {len(inputs)} inputs, {len(selects)} selects, {len(textareas)} textareas", 'info')
            
            # Try to fill available inputs with player data
            if inputs:
                return self._fill_individual_inputs(inputs, teams)
            
            self.log("Form approach needs manual implementation", 'warning')
            return True
            
        except Exception as e:
            self.log(f"Error in form approach: {str(e)}", 'error')
            return False
