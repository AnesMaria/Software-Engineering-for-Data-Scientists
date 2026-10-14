"""Employee datasets for reporting and prediction."""
from .query_base import QueryBase


class Employee(QueryBase):
    name = "employee"

    def names(self):
        return self.query("SELECT first_name || ' ' || last_name, employee_id FROM employee ORDER BY employee_id")

    def username(self, id):
        return self.query("SELECT first_name || ' ' || last_name FROM employee WHERE employee_id = ?", (id,))

    def model_data(self, id):
        sql = f"""
                    SELECT SUM(positive_events) positive_events
                         , SUM(negative_events) negative_events
                    FROM {self.name}
                    JOIN employee_events
                        USING({self.name}_id)
                    WHERE {self.name}.{self.name}_id = ?
                """
        return self.pandas_query(sql, (id,))