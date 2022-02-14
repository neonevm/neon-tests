from locust import HttpUser, task, between


class Web3User(HttpUser):
    wait_time = between(1, 5)