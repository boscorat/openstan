from openstan.views.admin_view import AdminView
from openstan.views.balance_chart_view import BalanceChartView
from openstan.views.content_view import ContentFrameView
from openstan.views.footer_view import FooterView
from openstan.views.project_view import ProjectView as ProjectView
from openstan.views.statement_queue_view import StatementQueueView
from openstan.views.statement_result_view import StatementResultView
from openstan.views.title import TitleView

__all__: list[str] = [
    "AdminView",
    "BalanceChartView",
    "ProjectView",
    "StatementQueueView",
    "StatementResultView",
    "TitleView",
    "FooterView",
    "ContentFrameView",
]
