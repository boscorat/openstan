from openstan.views.admin_view import AdminView
from openstan.views.content_view import ContentFrameView
from openstan.views.footer_view import FooterView
from openstan.views.project_info_view import ProjectInfoView as ProjectInfoView
from openstan.views.project_view import ProjectNavView as ProjectNavView
from openstan.views.project_view import ProjectView as ProjectView
from openstan.views.statement_queue_view import StatementQueueView
from openstan.views.statement_result_view import StatementResultView
from openstan.views.stub_views import ExportDataView, RunReportsView
from openstan.views.title import TitleView

__all__: list[str] = [
    "AdminView",
    "ProjectView",
    "ProjectNavView",
    "ProjectInfoView",
    "ExportDataView",
    "RunReportsView",
    "StatementQueueView",
    "StatementResultView",
    "TitleView",
    "FooterView",
    "ContentFrameView",
]
