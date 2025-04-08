from django.utils.translation import gettext as _
from django.contrib import admin as admin
from django.template.response import TemplateResponse
from django.db.models import Prefetch

from oioioi.contests.models import SubmissionReport, ScoreReport
from oioioi.base import admin as oioioiadmin
from oioioi.problems.models import ProblemName
from oioioi.rejudgemgr.models import Rejudge, RejudgeRelation


class RejudgeAdmin(oioioiadmin.ModelAdmin):
    list_display = ("id", "comment", "date")
    list_display_links = ("id",)
    actions = None

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = (
            RejudgeRelation.objects.filter(rejudge_id=object_id)
            # .select_related(
            #     "submit",
            #     "submit__user",
            #     "submit__problem_instance",
            #     "submit__problem_instance__problem",
            # )
            # .prefetch_related(
            #     "rj_former",
            #     "rj_newer",
            #     "rj_newer__scorereport_set",
            #     "rj_former__scorereport_set",
            #     "rj_former__submission__problem_instance__problem__names",
            #     "rj_newer__submission__problem_instance__problem__names",
            #     # "submit__problem_instance__problem__names",
            # )
            .all()
        )
        changed_list = []
        unchanged_list = []
        unjudged_list = []
        for a in obj:
            # Find out the submission score (from SubmissionReport's' ScoreReport(s?))
            # NOTE: This assumes only one ScoreReport has a score, which might not
            #       always be the case!!!
            score_old = None
            score_new = None
            for r in a.rj_former.all():
                sr = r.score_report
                if sr is not None and sr.score is not None:
                    score_old = sr
                    break
            for r in a.rj_newer.all():
                sr = r.score_report
                if sr is not None and sr.score is not None:
                    score_new = sr
                    break
            # Try to determine score diff.
            # If ScoreValue has an int representation - number difference,
            # otherwise try a simple boolean comparison.
            # Fallback is the error name (which should be the default ScoreValue.__ne__() - NotImplemented)
            try:
                score_diff = score_new.score.to_int() - score_old.score.to_int()
            except Exception as x:
                print(x)
                try:
                    score_diff = score_new.score != score_old.score
                except Exception as e:
                    score_diff = e.__class__.__name__  # to avoid outright crashing the page and at least let know the reader that something went wrong
            # Separate lists for presentation reasons.
            # See: oioioi/rejudgemgr/templates/admin/rejudgemgr/rejudge/change_form.html
            dict_to_append = {
                "submission": a.submit,
                "reports_old": a.rj_former.all(),
                "reports_new": a.rj_newer.all(),
                "score_old": score_old,
                "score_new": score_new,
            }
            if score_new is None:
                unjudged_list.append(dict_to_append)
            else:
                dict_to_append["score_diff"] = score_diff
                if len(dict_to_append["reports_old"]) != len(
                    dict_to_append["reports_new"]
                ):
                    dict_to_append["warning"] = f"""Unequal number of SubmissionReports.
                            <br>
                            <b>Before: {len(dict_to_append["reports_old"])}
                            <br>After: {len(dict_to_append["reports_new"])}</b>
                            <br>Submission has not finished judging, you somehow e.g. made a "FULL" report for a "INITIAL"+"NORMAL" report, or something worse."""
                if (
                    score_diff == 0 or not score_diff
                ):  # Checking only for "False", None check is above
                    unchanged_list.append(dict_to_append)
                else:
                    changed_list.append(dict_to_append)
                    # "score_diff_str": f"+{score_diff}" if (isinstance(score_diff, int) and score_diff > 0) else score_diff,
        # Fill context (Not writing directly to context dict for readability)
        extra_context = extra_context or {}
        extra_context["rejudge"] = {
            "unchanged_list": unchanged_list,
            "changed_list": sorted(changed_list, key=lambda a: a["score_diff"]),
            "unjudged_list": unjudged_list,
        }
        assert len(obj) == len(unchanged_list) + len(changed_list) + len(
            unjudged_list
        )  # sanity check
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )


oioioiadmin.site.register(Rejudge, RejudgeAdmin)
