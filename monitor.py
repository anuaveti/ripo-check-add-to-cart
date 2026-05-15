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
        self.driver.implicitly_wait(3)  # fast
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
        """Quick popup closer – tries once, no loops."""
        try:
            # Try common close buttons
            for selector in [".popup-close", ".close-popup", ".modal-close", ".close", "button[aria-label='Close']", "button.close"]:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.is_displayed():
                        self._click_element(driver, elem)
                        print("Closed popup")
                        return
                except:
                    pass
            # Try dismiss buttons
            for text in ["No thanks", "Dismiss", "Decline", "Not now"]:
                try:
                    elem = driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                    if elem.is_displayed():
                        self._click_element(driver, elem)
                        print("Closed popup")
                        return
                except:
                    pass
            # Press Escape
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except:
            pass

    def _get_windows_menu_link(self, driver, wait):
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".main-navigation, .site-header, nav")))
        menu_links = driver.find_elements(By.CSS_SELECTOR, ".main-navigation ul > li > a, .site-header nav ul > li > a, nav ul > li > a")
        if not menu_links:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            menu_links = [l for l in all_links if l.get_attribute("href") and l.get_attribute("href").startswith("https://insectnets.com/") and len(l.text.strip()) > 3]
        if not menu_links:
            raise Exception("No menu links")
        idx = 1 if len(menu_links) > 1 and menu_links[0].text.strip().lower() == "home" else 0
        return menu_links[idx]

    def _get_doors_menu_link(self, driver, wait):
        menu_links = driver.find_elements(By.CSS_SELECTOR, ".main-navigation ul > li > a, .site-header nav ul > li > a")
        if len(menu_links) > 1:
            return menu_links[1]
        return driver.find_element(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'durv')]")

    def _expand_accordion(self, driver, wait, header_selector):
        try:
            header = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, header_selector)))
            self._click_element(driver, header)
            time.sleep(0.1)
        except:
            pass

    def _add_product_to_cart(self, driver, wait):
        """Simplified add to cart – only expands the two main accordions (net and frame) for windows."""
        try:
            self._expand_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title")
            self._expand_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title")
            add_button = driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt")
            driver.execute_script("arguments[0].scrollIntoView();", add_button)
            add_button.click()
            time.sleep(0.3)
            # Close overlay if appears
            try:
                overlay = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.overlay.open")))
                overlay.click()
            except:
                pass
            return True
        except Exception as e:
            print(f"Add to cart error: {e}")
            return False

    def _add_door_product_to_cart(self, driver, wait):
        """Add door product – expands the many door accordions."""
        accordions = [
            "#attr-acc-pa_obstractions-header > span.attr-accordion__title",
            "#attr-acc-pa_mounting-type-door-header",
            "#attr-acc-dimensions-header > span.attr-accordion__title",
            "#attr-acc-pa_opening-direction-header > span.attr-accordion__title",
            "#attr-acc-pa_dimension-type-header > span.attr-accordion__title",
            "#attr-acc-pa_net-type-header > span.attr-accordion__title",
            "#attr-acc-pa_petscreen-in-lower-part-header > span.attr-accordion__title",
            "#attr-acc-pa_frame-color-header > span.attr-accordion__title"
        ]
        for sel in accordions:
            self._expand_accordion(driver, wait, sel)
        add_button = driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt")
        driver.execute_script("arguments[0].scrollIntoView();", add_button)
        add_button.click()
        time.sleep(0.3)
        try:
            overlay = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.overlay.open")))
            overlay.click()
        except:
            pass
        return True

    def test_ripo_add_to_cart(self):
        global _screenshot_path
        driver = self.driver
        wait = WebDriverWait(driver, 20)  # reduced timeout

        # Homepage
        driver.get("https://insectnets.com/")
        print("Page loaded:", driver.current_url)
        time.sleep(0.5)
        self._close_any_popup(driver, wait)

        # Geoip popup (if present)
        try:
            geo = wait.until(EC.element_to_be_clickable((By.ID, "geoip-popup-switch-yes")))
            geo.click()
        except:
            pass

        # Cookie consent
        try:
            cookie = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-cky-tag=\"reject-button\"]")))
            cookie.click()
        except:
            pass
        time.sleep(0.3)

        # Helper to go to windows category and click product by index
        def go_to_windows():
            link = self._get_windows_menu_link(driver, wait)
            link.click()
            time.sleep(0.3)
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid-item"))

        def click_product(idx):
            products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item")))
            driver.execute_script("arguments[0].scrollIntoView();", products[idx])
            products[idx].click()
            time.sleep(0.3)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))

        # ---- Add 3 windows products ----
        for idx in [1, 0, 2]:  # second, first, third
            go_to_windows()
            click_product(idx)
            self._add_product_to_cart(driver, wait)

        # ---- Doors category ----
        def go_to_doors():
            link = self._get_doors_menu_link(driver, wait)
            link.click()
            time.sleep(0.3)
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid-item"))

        # First door product (index 0)
        go_to_doors()
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item")))
        driver.execute_script("arguments[0].scrollIntoView();", products[0])
        products[0].click()
        time.sleep(0.3)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._add_door_product_to_cart(driver, wait)

        # Fifth door product (index 4)
        go_to_doors()
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item")))
        if len(products) <= 4:
            raise Exception("Not enough door products")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", products[4])
        time.sleep(0.2)
        products[4].click()
        time.sleep(0.3)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        # For fifth product, only two accordions
        self._expand_accordion(driver, wait, "#attr-acc-pa_installation-type-header > span.attr-accordion__title")
        self._expand_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title")
        add_button = driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt")
        driver.execute_script("arguments[0].scrollIntoView();", add_button)
        add_button.click()
        time.sleep(0.3)

        # ---- Go to cart page ----
        try:
            cart_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.wc-forward.btn.btn-color-secondary.btn-size-large")))
            driver.execute_script("arguments[0].click();", cart_link)
        except:
            # Fallback XPath
            cart_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'View cart')]")))
            driver.execute_script("arguments[0].click();", cart_link)

        time.sleep(1)
        # Wait for cart table
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".cart_item"))
        print("Cart page loaded")

        # ---- Screenshot ----
        screenshot_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        screenshot_path = screenshot_file.name
        screenshot_file.close()
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved")
        _screenshot_path = screenshot_path

        # ---- Verify cart count ----
        cart_items = driver.find_elements(By.CSS_SELECTOR, ".cart_item")
        actual_count = len(cart_items)
        print(f"Cart contains {actual_count} items.")
        if actual_count != 5:
            # Refresh once to be sure
            driver.refresh()
            time.sleep(0.5)
            cart_items = driver.find_elements(By.CSS_SELECTOR, ".cart_item")
            actual_count = len(cart_items)
            if actual_count != 5:
                raise AssertionError(f"Cart has {actual_count} items, expected 5.")

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
            return True
        except NoSuchElementException:
            return False

    def is_alert_present(self):
        try:
            self.driver.switch_to.alert
            return True
        except NoAlertPresentException:
            return False

    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to.alert
            text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return text
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
        except:
            pass
