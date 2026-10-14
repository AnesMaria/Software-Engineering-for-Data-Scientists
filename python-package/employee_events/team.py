"""Team datasets for reporting and prediction."""
from .query_base import QueryBase


class Team(QueryBase):
    name = "team"

    def names(self):
        return self.query("SELECT team_name, team_id FROM team ORDER BY team_id")

    def username(self, id):
        return self.query("SELECT team_name FROM team WHERE team_id = ?", (id,))

    def model_data(self, id):
        sql = f"""
            SELECT positive_events, negative_events FROM (
                    SELECT employee_id
                         , SUM(positive_events) positive_events
                         , SUM(negative_events) negative_events
                    FROM {self.name}
                    JOIN employee_events
                        USING({self.name}_id)
                    WHERE {self.name}.{self.name}_id = ?
                    GROUP BY employee_id
                   )
                """
        return self.pandas_query(sql, (id,))