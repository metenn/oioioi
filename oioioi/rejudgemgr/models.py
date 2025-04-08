from typing import List, Union
from django.db import models, transaction
from django.utils.translation import gettext as _

from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.contests.models import Submission, SubmissionReport


class Rejudge(models.Model):
    comment = models.CharField(
        _("Comment"), max_length=100
    )
    date = models.DateTimeField(
        _("Issued at"), auto_now=False, auto_now_add=True
    )

    @staticmethod
    def record(submission: Submission, comment: Union[str, None] = None):
        print(f"Rejudge! {submission=}, {comment=}.")
        # print("cd", submission, comment, "cd!!")
        com = comment or f"Unknown rejudge for submission {submission.id}"
        print(f"Rejudge2 {submission=}, {comment=}.")
        return Rejudge.record_many(
            [
                submission,
            ],
            comment=com,
        )

    @staticmethod
    def record_many(subs: List[Submission], comment: Union[str, None] = None):
        print(f"Rejudge_manu! {subs=}, {comment=}.")
        com = comment or "A group rejudge"
        print(f"Rejudge_manu2! {subs=}, {comment=}.")
        with transaction.atomic():
            rejudge_record = Rejudge(comment=com)
            rejudge_record.save()
            for s in subs:
                formers = SubmissionReport.objects.filter(
                    submission=s, status="ACTIVE"
                ).all()
                relation = RejudgeRelation(rejudge=rejudge_record, submit=s)
                relation.save()
                relation.rj_former.add(*formers)
        return rejudge_record


class RejudgeRelation(models.Model):
    rejudge = models.ForeignKey(to="rejudgemgr.Rejudge", on_delete=models.CASCADE)
    submit = models.ForeignKey(to="contests.Submission", on_delete=models.CASCADE)
    # Submission report(s) that were status=ACTIVE before rejudge (status=SUPERSEDED after)
    rj_former = models.ManyToManyField(
        "contests.SubmissionReport",
        related_name="rj_former",
        verbose_name=_(
            "Before"
        ),
        blank=False,
    )
    # List of submission reports created and made status=ACTIVE after rejudge
    rj_newer = models.ManyToManyField(
        "contests.SubmissionReport",
        related_name="rj_newer",
        verbose_name=_(
            "After"
        ),
        blank=True,
    )
    
    def accept_rejudge(self, update_user_results=True):
        with transaction.atomic():
            for old_sr in self.rj_former.all():
                old_sr.status = "SUPERSEDED"
                old_sr.save()
            for new_sr in self.rj_former.all():
                new_sr.status = "ACTIVE"
                new_sr.save()
        if update_user_results:
            self.submit.problem_instance.problem.contest.controller.update_user_results(self.submit.user, self.submit.problem_instance)

    class Meta:
        unique_together = ("rejudge", "submit")
