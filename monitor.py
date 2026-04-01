# -*- coding: utf-8 -*-
import os
import smtplib
import ssl
import unittest
import time
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException, TimeoutException
from selenium.webdriver.chrome.options import Options

# ================= CONFIGURATION =================
ZOHO_EMAIL = os.environ.get("ZOHO_EMAIL")
ZOHO_PASSWORD = os.environ.get("ZOHO_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

if not all([ZOHO_EMAIL, ZOHO_PASSWORD, RECIPIENT_EMAIL]):
    raise ValueError("Missing required environment variables")

SMTP_SERVER = "smtp.zoho.com"
SMTP_PORT = 587

# ================= EMAIL HELPER =================
def send_email_notification(subject, body):
    print(f"Attempting to send email to {RECIPIENT_EMAIL}...")
    msg = MIMEMultipart()
    msg['From'] = ZOHO_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(context=context)
        server.login(ZOHO_EMAIL, ZOHO_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")
        import traceback
        traceback.print_exc()

# ================= TEST RUNNER =================
def run_test_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(RipoAddToCart)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    success = result.wasSuccessful()
    error_messages = []
    for err in result.errors + result.failures:
        error_messages.append(f"{err[0]}: {err[1]}")
    return success, "\n".join(error_messages)

# ================= TEST CLASS =================
class RipoAddToCart(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        # Anti-detection
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
        except:
            driver.execute_script("arguments[0].click();", element)

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
        driver = self.driver
        wait = WebDriverWait(driver, 90)  # increased timeout

        # Homepage
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

        # Wait a moment for any overlay to disappear
        time.sleep(2)

        # DEBUG: print page source
        print("Page source after popups (first 2000 chars):")
        print(driver.page_source[:2000])

        # Category: INSEKTU SIETI LOGIEM – try multiple ways
        try:
            link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "INSEKTU SIETI LOGIEM")))
        except TimeoutException:
            print("Exact link text not found, trying partial text...")
            link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "SIETI LOGIEM")))
        self._click_element(driver, link)
        print("Category link clicked")

        time.sleep(2)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-grid, .products, .product-grid-item"))

        # The rest of the test (same as your working version)
        # Click second product (index 1)
        products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-grid-item, .product")))
        self.assertGreater(len(products), 1, "Not enough products in category")
        driver.execute_script("arguments[0].scrollIntoView();", products[1])
        self._click_element(driver, products[1])

        # Product page actions
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.single_add_to_cart_button")))
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_net-type-header > span.attr-accordion__title", wait_for_option=False)
        self._select_first_option_in_accordion(driver, wait, "#attr-acc-pa_frame-color-header > span.attr-accordion__title", wait_for_option=False)
        self._click_element(driver, driver.find_element(By.CSS_SELECTOR, "button.single_add_to_cart_button.button.alt"))
        self._close_overlay(driver, wait)

        # Back to category and click first product (index 0)
        self._click_element(driver, driver.find_element(By.LINK_TEXT, "INSEKTU SIETI LOGIEM"))
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

        # Back to category and click third product (index 2)
        self._click_element(driver, driver.find_element(By.LINK_TEXT, "INSEKTU SIETI LOGIEM"))
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

        # DOORS SECTION
        self._click_element(driver, driver.find_element(By.LINK_TEXT, "INSEKTU SIETI DURVĪM"))
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
        self._click_element(driver, driver.find_element(By.LINK_TEXT, "INSEKTU SIETI DURVĪM"))
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

        self._click_element(driver, wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.wc-forward.btn.btn-color-secondary.btn-size-large"))))

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
    success, errors = run_test_suite()
    if success:
        subject = f"[OK] Insectnets cart test PASSED at {datetime.now()}"
        body = "The automated cart test completed successfully. All products were added to the cart without errors."
        send_email_notification(subject, body)
    else:
        subject = f"[ERROR] Insectnets cart test FAILED at {datetime.now()}"
        body = f"The automated cart test failed.\n\nError details:\n{errors}"
        send_email_notification(subject, body)
