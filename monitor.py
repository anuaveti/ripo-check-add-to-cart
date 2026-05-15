# -*- coding: utf-8 -*-
import os
import smtplib
import ssl
import unittest
import time
import tempfile
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# ================= CONFIGURATION =================
ZOHO_EMAIL = os.environ.get("ZOHO_EMAIL")
ZOHO_PASSWORD = os.environ.get("ZOHO_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

if not all([ZOHO_EMAIL, ZOHO_PASSWORD, RECIPIENT_EMAIL]):
    raise ValueError("Missing required environment variables")

SMTP_SERVERS = ["smtp.zoho.com", "smtp.zoho.eu"]
SMTP_PORT = 587

# ================= EMAIL HELPER =================
def send_email_notification(subject, body, image_path=None):
    print(f"Attempting to send email to {RECIPIENT_EMAIL}...")
    msg = MIMEMultipart()
    msg['From'] = ZOHO_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as f:
                img = MIMEImage(f.read(), name=os.path.basename(image_path))
                msg.attach(img)
            print("Screenshot attached")
        except Exception as e:
            print(f"Could not attach screenshot: {e}")
    else:
        print("No screenshot to attach")

    for server in SMTP_SERVERS:
        try:
            context = ssl.create_default_context()
            server_obj = smtplib.SMTP(server, SMTP_PORT)
            server_obj.starttls(context=context)
            server_obj.login(ZOHO_EMAIL, ZOHO_PASSWORD)
            server_obj.send_message(msg)
            server_obj.quit()
            print(f"Email sent successfully using {server}")
            return True
        except Exception as e:
            print(f"Failed with {server}: {e}")
            continue

    print("All SMTP servers failed.")
    return False

# ================= TEST RUNNER =================
_screenshot_path = None

def run_test_suite():
    global _screenshot_path
    suite = unittest.TestLoader().loadTestsFromTestCase(RipoAddToCart)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    success = result.wasSuccessful()
    error_messages = []
    for err in result.errors + result.failures:
        error_messages.append(f"{err[0]}: {err[1]}")
    return success, "\n".join(error_messages), _screenshot_path

# ================= TEST CLASS =================
class RipoAddToCart(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.base_url = "https://www.blazedemo.com/"
        self.verificationErrors = []
        self.accept_next_alert = True

    def _click_element(self, driver, element):
        try:
            element.click()
        except StaleElementReferenceException:
            raise
        except:
            driver.execute_script("arguments[0].click();", element)

    def _close_any_popup(self, driver, wait):
        """Aggressively close any popup/modal."""
        close_selectors = [
            (By.CSS_SELECTOR, ".popup-close, .close-popup, .modal-close, .close"),
            (By.CSS_SELECTOR, "button[aria-label='Close']"),
            (By.CSS_SELECTOR, "button.close"),
            (By.XPATH, "//button[contains(text(), 'Close')]"),
            (By.XPATH, "//button[contains(text(), '×')]"),
            (By.XPATH, "//span[contains(text(), '×')]"),
            (By.CSS_SELECTOR, ".newsletter-popup .close"),
            (By.CSS_SELECTOR, ".popup .close"),
            (By.CSS_SELECTOR, "div[role='dialog'] button"),
        ]
        dismiss_selectors = [
            (By.XPATH, "//button[contains(text(), 'No thanks')]"),
            (By.XPATH, "//button[contains(text(), 'Dismiss')]"),
            (By.XPATH, "//button[contains(text(), 'Decline')]"),
            (By.XPATH, "//button[contains(text(), 'Not now')]"),
            (By.XPATH, "//button[contains(text(), 'Maybe later')]"),
        ]
        continue_selectors = [
            (By.XPATH, "//button[contains(text(), 'Continue')]"),
            (By.XPATH, "//button[contains(text(), 'Continue shopping')]"),
            (By.XPATH, "//a[contains(text(), 'Continue')]"),
            (By.XPATH, "//a[contains(text(), 'Continue shopping')]"),
            (By.XPATH, "//button[contains(text(), 'Back to site')]"),
            (By.XPATH, "//button[contains(text(), 'Stay here')]"),
            (By.XPATH, "//a[contains(text(), 'Back to site')]"),
            (By.XPATH, "//button[contains(text(), 'OK')]"),
        ]
        for by, selector in close_selectors + dismiss_selectors + continue_selectors:
            try:
                elem = driver.find_element(by, selector)
                if elem.is_displayed() and elem.is_enabled():
                    self._click_element(driver, elem)
                    print(f"Closed popup using: {selector}")
                    time.sleep(0.2)
                    return True
            except:
                continue
        # Press Escape
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            print("Sent Escape key to close popup")
            time.sleep(0.2)
            return True
        except:
            pass
        return False

    def _get_windows_menu_link(self, driver, wait):
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".main-navigation, .site-header, nav, .menu-primary-container")))
        menu_selectors = [
            ".main-navigation ul > li > a",
            ".site-header nav ul > li > a",
            "nav ul > li > a",
            ".menu-primary-container ul > li > a",
            ".menu > li > a"
        ]
        menu_links = []
        for selector in menu_selectors:
            menu_links = driver.find_elements(By.CSS_SELECTOR, selector)
            if menu_links:
                print(f"Found menu links using selector: {selector}")
                break
        if not menu_links:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href")
                if href and href.startswith("https://insectnets.com/") and len(link.text.strip()) > 3:
                    menu_links.append(link)
            if menu_links:
                print("Using fallback link detection")
        if not menu_links:
            raise Exception("Could not find any menu links")
        idx = 0
        if len(menu_links) > 1 and menu_links[0].text.strip().lower() == "home":
            idx = 1
        return menu_links[idx]

    def _get_doors_menu_link(self, driver, wait):
        try:
            menu_selectors = [
                ".main-navigation ul > li > a",
                ".site-header nav ul > li > a",
                "nav ul > li > a",
                ".menu-primary-container ul > li > a",
                ".menu > li > a"
            ]
            menu_links = []
            for selector in menu_selectors:
                menu_links = driver.find_elements(By.CSS_SELECTOR, selector)
                if menu_links:
                    break
            if len(menu_links) > 1:
                return menu_links[1]
        except:
            pass
        door_link = driver.find_element(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'durv')]")
        return door_link

    def _select_first_option_in_accordion(self, driver, wait, header_selector, wait_for_option=True, timeout=1):
        try:
            header = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, header_selector)))
            self._click_element(driver, header)
            time.sleep(0.1)
            if header_selector.startswith('#') and wait_for_option:
                panel_id = header_selector.split('>')[0].strip() + '-panel'
                try:
                    option = WebDriverWait(driver, timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, f"{panel_id} .option, {panel_id} label, {panel_id} input, {panel_id} button"))
                    )
                    self._click_element(driver, option)
                except TimeoutException:
                    pass
        except Exception:
            pass

    def _add_product_to_cart(self, driver, wait, product_name=""):
        """
        Perform the add-to-cart process on the current product page.
        Returns True if successfully added, False otherwise.
        """
        try:
            # Wait for the add-to-cart button to be present
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt")))
            # Expand necessary accordions (only those that exist – the script will click if present)
            # For windows products (net-type and frame-color)
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            # Additional accordions for some products
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_mounting-type-window-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-dimensions-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_dimension-type-header", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header", wait_for_option=False)
            except:
                pass
            # Door-specific accordions
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_obstractions-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_mounting-type-door-header", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_opening-direction-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_petscreen-in-lower-part-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass
            try:
                self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_installation-type-header > span.attr-accordion__title", wait_for_option=False)
            except:
                pass

            # Click add to cart button
            add_button = driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt")
            driver.execute_script("arguments[0].scrollIntoView();", add_button)
            add_button.click()
            print(f"Added product: {product_name}")
            # Wait for success message or overlay
            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".woocommerce-message, .added-to-cart, .cart-popup, div.overlay.open"))
                )
            except:
                pass
            # Close any overlay that appears
            self._close_overlay(driver, wait)
            return True
        except Exception as e:
            print(f"Error adding product {product_name}: {e}")
            return False

    def _close_overlay(self, driver, wait):
        try:
            overlay = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.overlay.open"))
            )
            self._click_element(driver, overlay)
        except TimeoutException:
            pass

    def test_ripo_add_to_cart(self):
        global _screenshot_path
        driver = self.driver
        wait = WebDriverWait(driver, 90)

        # ---- Homepage loading with retry ----
        for attempt in range(3):
            try:
                driver.get("https://insectnets.com/")
                print("Page loaded:", driver.current_url)
                break
            except Exception as e:
                print(f"Attempt {attempt+1} failed to load homepage: {e}")
                if attempt == 2:
                    raise
                time.sleep(5)
        time.sleep(2)
        self._close_any_popup(driver, wait)

        # ---- Geoip popup ----
        geoip_clicked = False
        for by, selector in [
            (By.ID, "geoip-popup-switch-yes"),
            (By.CSS_SELECTOR, ".geoip-popup-switch-yes"),
            (By.XPATH, "//button[contains(text(), 'Yes')]"),
            (By.XPATH, "//button[contains(text(), 'Switch')]")
        ]:
            try:
                elem = wait.until(EC.element_to_be_clickable((by, selector)))
                self._click_element(driver, elem)
                geoip_clicked = True
                print("Geoip popup clicked")
                break
            except TimeoutException:
                continue
        if not geoip_clicked:
            print("Geoip popup not found – continuing")

        # ---- Cookie consent ----
        cookie_clicked = False
        for by, selector in [
            (By.CSS_SELECTOR, "[data-cky-tag=\"reject-button\"]"),
            (By.CSS_SELECTOR, ".cky-reject-button"),
            (By.XPATH, "//button[contains(text(), 'Reject')]"),
            (By.XPATH, "//button[contains(text(), 'Decline')]")
        ]:
            try:
                elem = wait.until(EC.element_to_be_clickable((by, selector)))
                self._click_element(driver, elem)
                cookie_clicked = True
                print("Cookie popup clicked")
                break
            except TimeoutException:
                continue
        if not cookie_clicked:
            print("Cookie popup not found – continuing")

        time.sleep(0.5)

        # ---- Helper to navigate to windows category ----
        def go_to_windows_category():
            windows_link = self._get_windows_menu_link(driver, wait)
            print(f"Clicking windows menu link: '{windows_link.text}'")
            self._click_element(driver, windows_link)
            time.sleep(0.5)
            self._close_any_popup(driver, wait)
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))

        # ---- Helper to get product link and click ----
        def click_product(index, product_name):
            products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
            if len(products) <= index:
                raise Exception(f"Not enough products to click index {index} for {product_name}")
            product = products[index]
            driver.execute_script("arguments[0].scrollIntoView();", product)
            self._click_element(driver, product)
            time.sleep(0.5)
            self._close_any_popup(driver, wait)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))

        # ---- Add products with retries ----
        product_list = [
            (1, "second product"),
            (0, "first product"),
            (2, "third product")
        ]
        for idx, name in product_list:
            go_to_windows_category()
            click_product(idx, name)
            added = False
            for retry in range(2):
                if self._add_product_to_cart(driver, wait, name):
                    added = True
                    break
                else:
                    print(f"Retry adding {name} (attempt {retry+2})")
                    # Refresh product page and try again
                    driver.refresh()
                    time.sleep(1)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
            if not added:
                raise Exception(f"Failed to add {name} after 2 attempts")

        # ---- Doors category ----
        def go_to_doors_category():
            doors_link = self._get_doors_menu_link(driver, wait)
            print(f"Clicking doors menu link: '{doors_link.text}'")
            self._click_element(driver, doors_link)
            time.sleep(0.5)
            self._close_any_popup(driver, wait)
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))

        door_products = [
            (0, "first door product"),
            (4, "fifth door product")
        ]
        for idx, name in door_products:
            go_to_doors_category()
            click_product(idx, name)
            added = False
            for retry in range(2):
                if self._add_product_to_cart(driver, wait, name):
                    added = True
                    break
                else:
                    print(f"Retry adding {name} (attempt {retry+2})")
                    driver.refresh()
                    time.sleep(1)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
            if not added:
                raise Exception(f"Failed to add {name} after 2 attempts")

        # ---- Go to cart page with robust handling ----
        cart_clicked = False
        for attempt in range(5):
            try:
                # Re-find element each time
                cart_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.wc-forward.btn.btn-color-secondary.btn-size-large")))
                driver.execute_script("arguments[0].click();", cart_link)
                cart_clicked = True
                print("Cart link clicked")
                break
            except (StaleElementReferenceException, TimeoutException) as e:
                print(f"Cart link attempt {attempt+1} failed: {e}")
                if attempt == 4:
                    # Fallback to XPath
                    try:
                        cart_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'View cart') or contains(text(), 'Cart')]")))
                        driver.execute_script("arguments[0].click();", cart_link)
                        cart_clicked = True
                        print("Cart link clicked using fallback XPath")
                        break
                    except Exception as final_err:
                        raise final_err
                time.sleep(1)
        if not cart_clicked:
            raise Exception("Could not click the cart link")

        # Wait for cart page to load
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".cart_item, .cart-table, .woocommerce-cart-form"))
        time.sleep(2)
        print("Cart page loaded")

        # ---- Take screenshot ----
        screenshot_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        screenshot_path = screenshot_file.name
        screenshot_file.close()
        self.driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        _screenshot_path = screenshot_path

        # ---- Verify cart item count ----
        cart_items = driver.find_elements(By.CSS_SELECTOR, ".cart_item")
        actual_count = len(cart_items)
        print(f"Cart contains {actual_count} items.")
        if actual_count < 5:
            # Double-check by reloading the cart page once
            driver.refresh()
            time.sleep(2)
            cart_items = driver.find_elements(By.CSS_SELECTOR, ".cart_item")
            actual_count = len(cart_items)
            print(f"After refresh, cart contains {actual_count} items.")
            if actual_count < 5:
                raise AssertionError(f"Cart contains only {actual_count} items, expected 5. The cart may have missing products.")
        print("Cart item count verification passed.")

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def is_alert_present(self):
        try:
            self.driver.switch_to.alert
        except NoAlertPresentException:
            return False
        return True

    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally:
            self.accept_next_alert = True

    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    success, errors, screenshot_path = run_test_suite()
    if success:
        subject = f"[OK] Insectnets cart test PASSED at {datetime.now()}"
        body = "The automated cart test completed successfully. All products were added to the cart. Screenshot attached."
        send_email_notification(subject, body, image_path=screenshot_path)
    else:
        subject = f"[ERROR] Insectnets cart test FAILED at {datetime.now()}"
        body = f"Error details:\n{errors}"
        send_email_notification(subject, body, image_path=screenshot_path)

    if screenshot_path and os.path.exists(screenshot_path):
        try:
            os.unlink(screenshot_path)
            print("Screenshot file cleaned up")
        except:
            pass
