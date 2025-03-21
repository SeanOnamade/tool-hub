from locust import HttpUser, task, between
# locust performance test to simulate multiple users making API requests to see how well my API performs under load
# HttpUser is a simulated user
# task is a decorator to mark methods as tasks that the user will perform
# between is making users randomly wait between x and y seconds before their next request


class MyUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def list_tools(self):
        self.client.get("/tools?skip=0&limit=10")
        

    @task
    def search_tools(self):
        self.client.get("/tools/search?name=football&category=Public%20APIs&limit=10")