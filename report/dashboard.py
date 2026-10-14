"""FastHTML employee performance dashboard. Run from the repository root."""
import threading
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fasthtml.common import (
    fast_app, serve, Div, H1, H2, P, Title, Link, RedirectResponse, HTTPException,
)
from employee_events import QueryBase, Employee, Team
try:
    from .utils import load_model, project_root
    from .base_components import Dropdown, BaseComponent, Radio, MatplotlibViz, DataTable
    from .combined_components import FormGroup, CombinedComponent
except ImportError:
    from utils import load_model, project_root
    from base_components import Dropdown, BaseComponent, Radio, MatplotlibViz, DataTable
    from combined_components import FormGroup, CombinedComponent

plot_lock = threading.RLock()


class ReportDropdown(Dropdown):
    def build_component(self, entity_id, model):
        self.label = model.name.title()
        selector = super().build_component(str(entity_id), model)
        selector.attrs["id"] = "entity-choice"
        return selector

    def outer_div(self, child):
        from fasthtml.common import Label
        return Div(Label(self.label, _for="entity-choice"), child, id=self.id)

    def component_data(self, entity_id, model):
        return model.names()


class Header(BaseComponent):
    def build_component(self, entity_id, model):
        return Div(H1(f"{model.name.title()} Performance"),
                   P(model.username(entity_id)[0][0]))


class AccessibleChart(MatplotlibViz):
    alt = ""

    def build_component(self, entity_id, model):
        with plot_lock:
            image = super().build_component(entity_id, model)
        image.attrs["alt"] = self.alt
        image.attrs["src"] = image.attrs["src"].replace("image/jpg", "image/png")
        return image


class LineChart(AccessibleChart):
    alt = "Cumulative positive and negative employee performance events"

    def visualization(self, entity_id, model):
        data = model.event_counts(entity_id).fillna(0)
        data = data.set_index("event_date").sort_index().cumsum()
        data.columns = ["Positive", "Negative"]
        fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
        if data.empty:
            ax.text(.5, .5, "No performance events", ha="center", transform=ax.transAxes)
        else:
            data.plot(ax=ax, color=["#12805c", "#bd3545"])
        ax.set_title("Cumulative Performance Events")
        ax.set_xlabel("Date")
        ax.set_ylabel("Event count")
        self.set_axis_styling(ax, bordercolor="black", fontcolor="black")


class BarChart(AccessibleChart):
    predictor = load_model()
    alt = "Predicted recruitment probability, or average probability for the team"

    def visualization(self, entity_id, model):
        data = model.model_data(entity_id).dropna()
        fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
        if data.empty:
            ax.text(.5, .5, "Insufficient events for prediction", ha="center", transform=ax.transAxes)
        else:
            probabilities = self.predictor.predict_proba(data)
            positive_class = list(self.predictor.classes_).index(1)
            values = probabilities[:, positive_class]
            pred = float(values.mean() if model.name == "team" else values[0])
            ax.barh([""], [pred], color=plt.get_cmap("RdYlGn_r")(pred))
            ax.text(.5, .6, f"{pred:.1%}", transform=ax.transAxes, ha="center", fontsize=22)
        ax.set_xlim(0, 1)
        ax.set_title("Predicted Recruitment Risk")
        ax.set_xlabel("Average probability" if model.name == "team" else "Probability")
        self.set_axis_styling(ax, bordercolor="black", fontcolor="black")


class Visualizations(CombinedComponent):
    children = [LineChart(), BarChart()]
    outer_div_type = Div(cls="grid")


class NotesTable(DataTable):
    def component_data(self, entity_id, model):
        return model.notes(entity_id)


class DashboardFilters(FormGroup):
    id = "top-filters"
    action = "/update_data"
    method = "POST"
    children = [
        Radio(values=["Employee", "Team"], name="profile_type",
              hx_get="/update_dropdown", hx_target="#selector"),
        ReportDropdown(id="selector", name="user-selection"),
    ]


class Report(CombinedComponent):
    children = [Header(), DashboardFilters(), Visualizations(), H2("Manager Notes"),
                NotesTable(), P("Predictions support review; they do not establish why an employee may leave.")]


app, rt = fast_app(hdrs=(Link(rel="stylesheet", href="/assets/report.css"),))
report = Report()


def render_report(entity_id, model):
    if not model.username(entity_id):
        raise HTTPException(404, "Employee or team not found")
    return Title(f"{model.name.title()} Performance"), report(entity_id, model)


@app.get("/")
def index():
    names = Employee().names()
    if not names:
        raise HTTPException(404, "No employees available")
    return render_report(names[0][1], Employee())


@app.get("/employee/{id}")
def employee(id: int):
    return render_report(id, Employee())


@app.get("/team/{id}")
def team(id: int):
    return render_report(id, Team())


@app.get("/update_dropdown")
def update_dropdown(profile_type: str):
    if profile_type not in ("Employee", "Team"):
        raise HTTPException(400, "Invalid profile type")
    return DashboardFilters.children[1](None, Team() if profile_type == "Team" else Employee())


@app.post("/update_data")
async def update_data(request):
    data = await request.form()
    profile_type = data.get("profile_type")
    try:
        entity_id = int(data.get("user-selection", ""))
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid selection")
    if profile_type not in ("Employee", "Team"):
        raise HTTPException(400, "Invalid profile type")
    model = Employee() if profile_type == "Employee" else Team()
    if not model.username(entity_id):
        raise HTTPException(404, "Employee or team not found")
    return RedirectResponse(f"/{model.name}/{entity_id}", status_code=303)


@app.get("/assets/report.css")
def stylesheet():
    from starlette.responses import FileResponse
    return FileResponse(project_root / "assets" / "report.css", media_type="text/css")


if __name__ == "__main__":
    serve()