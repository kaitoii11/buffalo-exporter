import time
import os
from logging import getLogger
import prometheus_client
from prometheus_client import start_http_server, REGISTRY, Summary
from prometheus_client.core import CounterMetricFamily

logger = getLogger(__name__)

get_request_time = Summary("http_get_request_processing_seconds", 'HTTP GET Request Time to collect target')

class CustomCollector(object):
    def __init__(self, client, port=80, polling_interval_seconds=30):
        self.port = port
        self.polling_interval_seconds = polling_interval_seconds
        self.client = client
        self.metrics = {}

    def run_metrics_loop(self):
        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    @get_request_time.time()
    def fetch(self):
        self.client.login()
        self.metrics = self.client.getMetrics()

    def collect(self):
        for k, v in self.metrics.items():
            c = CounterMetricFamily(metric_names[0], "Total successfully sent packets", labels=['target'])
            c.add_metric([k], v[metric_names[0]])
            yield c
            c = CounterMetricFamily(metric_names[1], "Total error sent packets", labels=['target'])
            c.add_metric([k], v[metric_names[1]])
            yield c
            c = CounterMetricFamily(metric_names[2], "Total successfully received packets", labels=['target'])
            c.add_metric([k], v[metric_names[2]])
            yield c
            c = CounterMetricFamily(metric_names[3], "Total error received packets", labels=['target'])
            c.add_metric([k], v[metric_names[3]])
            yield c

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
metric_names = ['packet_sent_total', 'error_packet_sent_total','packet_received_total','error_packet_received']
entity_name = {"Internet側有線":"internet","LAN側有線(#1)":"lan1","LAN側有線(#2)":"lan2","LAN側有線(#3)":"lan3","LAN側無線(2.4GHz)":"wifi_2.4ghz", "LAN側無線(5GHz)":"wifi_5ghz" }
class Client:
    def __init__(self, url, password, username='admin'):
        self.url = url
        self.username = username
        self.password = password
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Chrome(options)
        self.loginpath = 'login.html'
        self.packetpath = 'packet.html'

    def login(self):
        self.driver.get(self.url + self.loginpath)
        self.driver.implicitly_wait(1)
        #driver.find_element(By.ID, 'form_USERNAME').send_keys(username)
        self.driver.find_element(By.ID, 'form_PASSWORD').send_keys(self.password)
        self.driver.find_element(By.CLASS_NAME,'button_login').click()

    def getMetrics(self):
        self.driver.get(self.url + self.packetpath)
        self.driver.implicitly_wait(1)
        tables = self.driver.find_elements(By.TAG_NAME, 'tr')
        metrics = {}
        ## Skip headers
        for i in range(2, len(tables)):
            if 'display: none' in tables[i].get_attribute('style'):
                continue
            th = tables[i].find_element(By.TAG_NAME, 'font')
            m = {}
            tds = tables[i].find_elements(By.TAG_NAME, 'td')
            for i, td in enumerate(tds):
                e = td.find_element(By.CLASS_NAME, 'DIGIT')
                m[metric_names[i]] =  e.text
            metrics[entity_name[th.text]] =  m

        return metrics


def main():
    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "10"))
    port = int(os.getenv("PORT","80"))

    url = os.getenv("URL")
    username = os.getenv("USERNAME","admin")
    password = os.getenv("PASSWORD")
    client = Client(url=url,
                    username=username,
                    password=password)

    metrics = CustomCollector(
            port=port,
            polling_interval_seconds=polling_interval_seconds,
            client=client
            )
    REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)
    REGISTRY.register(metrics)
    start_http_server(8000)
    metrics.run_metrics_loop()

if __name__ == "__main__":
    main()
