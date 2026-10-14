"""Shared employee and team reporting queries."""
from .sql_execution import QueryMixin


class QueryBase(QueryMixin):
    name = ""

    def names(self):
        return []

    def event_counts(self, id):
        return self.pandas_query(f"""
            SELECT event_date, SUM(positive_events) AS positive_events,
                   SUM(negative_events) AS negative_events
            FROM {self.name} JOIN employee_events USING ({self.name}_id)
            WHERE {self.name}.{self.name}_id = ?
            GROUP BY event_date ORDER BY event_date
        """, (id,))

    def notes(self, id):
        return self.pandas_query(f"""
            SELECT note_date, note FROM notes
            JOIN {self.name} USING ({self.name}_id)
            WHERE {self.name}.{self.name}_id = ?
            ORDER BY note_date, note
        """, (id,))