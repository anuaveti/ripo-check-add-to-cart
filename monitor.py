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

# ================= CONFIGURATION =================
ZOHO_EMAIL = os.environ.get("ZOHO_EMAIL")
ZOHO_PASSWORD = os.environ.get("ZOHO_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

if not all([ZOHO_EMAIL, ZOHO_PASSWORD, RECIPIENT_EMAIL]):
    raise ValueError("Missing required environment variables")

SMTP_SERVERS = ["smtp.zoho.com", "smtp.zoho.eu"]
SMTP_PORT = 587

# ================= EMAIL HELPER (with image attachment) =================
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
# Global variable to store screenshot path from test
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
    # After the test runs, the screenshot path is set in the test class attribute.
    # We need to capture it from the test instance. Since we don't have direct access,
    # we can use a class variable or a global. The test class sets the global.
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
        self.driver.implicitly_wait(30)
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

        # Homepage and popups
        driver.get("https://insectnets.com/")
        print("Page loaded:", driver.current_url)
        time.sleep(3)

        # Geoip popup
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

        # Cookie consent popup
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

        time.sleep(2)

        # ---- Windows category (second product) ----
        windows_link = self._get_windows_menu_link(driver, wait)
        print(f"Clicking windows menu link: '{windows_link.text}'")
        self._click_element(driver, windows_link)
        time.sleep(2)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))

        # Click second product (index 1)
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
        self.assertGreater(len(products), 1, "Not enough products in category")
        driver.execute_script("arguments[0].scrollIntoView();", products[1])
        self._click_element(driver, products[1])
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title", wait_for_option=False)
        self._click_element(driver, driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt"))
        self._close_overlay(driver, wait)

        # ---- First product ----
        driver.get("https://insectnets.com/")
        time.sleep(2)
        windows_link = self._get_windows_menu_link(driver, wait)
        self._click_element(driver, windows_link)
        time.sleep(2)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
        driver.execute_script("arguments[0].scrollIntoView();", products[0])
        self._click_element(driver, products[0])
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title", wait_for_option=False)
        self._click_element(driver, driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt"))
        self._close_overlay(driver, wait)

        # ---- Third product ----
        driver.get("https://insectnets.com/")
        time.sleep(2)
        windows_link = self._get_windows_menu_link(driver, wait)
        self._click_element(driver, windows_link)
        time.sleep(2)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
        self.assertGreater(len(products), 2, "Not enough products for third click")
        driver.execute_script("arguments[0].scrollIntoView();", products[2])
        self._click_element(driver, products[2])
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_mounting-type-window-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-dimensions-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_dimension-type-header", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header", wait_for_option=False)
        self._click_element(driver, driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt"))
        self._close_overlay(driver, wait)

        # ---- Doors category ----
        driver.get("https://insectnets.com/")
        time.sleep(2)
        doors_link = self._get_doors_menu_link(driver, wait)
        print(f"Clicking doors menu link: '{doors_link.text}'")
        self._click_element(driver, doors_link)
        time.sleep(2)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))

        # First door product
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
        self.assertGreater(len(products), 0, "No door products found")
        show_products = driver.find_elements(By.CSS_SELECTOR, ".product-grid-item.show .product-grid-item__image-hover picture img")
        door_product = show_products[0] if show_products else products[0]
        driver.execute_script("arguments[0].scrollIntoView();", door_product)
        self._click_element(driver, door_product)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_obstractions-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_mounting-type-door-header", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-dimensions-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_opening-direction-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_dimension-type-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_petscreen-in-lower-part-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title", wait_for_option=False)
        self._click_element(driver, driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt"))
        self._close_overlay(driver, wait)

        # Fifth door product
        driver.get("https://insectnets.com/")
        time.sleep(2)
        doors_link = self._get_doors_menu_link(driver, wait)
        self._click_element(driver, doors_link)
        time.sleep(2)
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".product-grid-item, .product")) > 4)
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
        self.assertGreater(len(products), 4, "Not enough door products")
        fifth_product = products[4]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", fifth_product)
        time.sleep(1)
        self._click_element(driver, fifth_product)
        wait_long = WebDriverWait(driver, 40)
        wait_long.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._select_first_option_in_accordion(driver, wait_long, "#attr-acc-pa_installation-type-header > span.attr-accordion__title", timeout=0.5)
        self._select_first_option_in_accordion(driver, wait_long, "#attr-acc-pa_frame-color-header > span.attr-accordion__title", timeout=0.5)
        add_to_cart_button = wait_long.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt")))
        driver.execute_script("arguments[0].scrollIntoView();", add_to_cart_button)
        self._click_element(driver, add_to_cart_button)

        # ---- Go to cart page and take screenshot ----
        cart_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.wc-forward.btn.btn-color-secondary.btn-size-large")))
        self._click_element(driver, cart_link)
        time.sleep(3)
        print("Cart page loaded, taking screenshot...")
        screenshot_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        screenshot_path = screenshot_file.name
        screenshot_file.close()
        self.driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        # Store in global variable for later email
        _screenshot_path = screenshot_path

        # After taking screenshot, count cart items(expected 5: 3 windows + 2 doors)
        cart_items = driver.find_elements(By.CSS_SELECTOR, ".cart_item")
        actual_count = len(cart_items)
        print(f"Cart contains {actual_count} items.")
        if actual_count < 5:
            raise AssertionError(f"Cart contains only {actual_count} items, expected 5. The cart may have missing products.")
    

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
        body = "The automated cart test completed successfully. All products were added to the cart. Screenshot attached. Cart contains {actual_count} items."
        send_email_notification(subject, body, image_path=screenshot_path)
    else:
        subject = f"[ERROR] Insectnets cart test FAILED at {datetime.now()}"
        body = f"Error details:\n{errors}"
        send_email_notification(subject, body)

    # Clean up screenshot if it exists
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            os.unlink(screenshot_path)
            print("Screenshot file cleaned up")
        except:
            pass
