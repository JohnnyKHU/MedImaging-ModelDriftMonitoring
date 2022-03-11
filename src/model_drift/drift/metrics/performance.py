import numpy as np
import torch
from sklearn import metrics
from torchmetrics.functional import auroc

from .base import BaseDriftCalculator


def macro_auc(scores, labels, skip_missing=True):
    if len(scores) == 0:
        return float('NaN')
    N = labels.shape[1]
    aucs = [0] * N
    for i in range(N):
        try:
            aucs[i] = auroc(torch.tensor(scores[i]), torch.tensor(labels[i]).long()).numpy()
        except Exception as e:
            if "No positive samples in targets" not in str(e):
                raise
            aucs[i] = float('NaN')

    aucs = np.array(aucs)
    c = (~np.isnan(aucs)).sum() if skip_missing else N
    return np.nansum(aucs) / c


def micro_auc(scores, labels):
    return float(auroc(torch.tensor(scores), torch.tensor(labels).long(), average='micro').numpy())


def classification_report(scores, labels, target_names=None, th=0.5, ):
    keeps = (labels.sum(axis=0) > 0)

    if target_names is None:
        target_names = [str(i) for i in range(scores.shape[1])]
    target_names = np.array(target_names)
    output = metrics.classification_report(labels, scores >= th, target_names=target_names, output_dict=True)
    for i, k in enumerate(target_names):
        if keeps[i] == 0:
            continue
        output[k]['auroc'] = metrics.roc_auc_score(
            labels[:, i], scores[:, i])

    output['macro avg']['auroc'] = (metrics.roc_auc_score(
        labels[:, keeps], scores[:, keeps], labels=target_names[keeps], average='macro'))
    output['micro avg']['auroc'] = (metrics.roc_auc_score(labels, scores, average='micro'))

    return output


class AUROCCalculator(BaseDriftCalculator):
    name = "auroc"

    def __init__(self, ref=None, label_col=None, score_col=None, average='micro', ignore_nan=True):
        super().__init__(None)
        self.label_col = label_col
        self.score_col = score_col
        self.average = average

    def _predict(self, sample):
        labels = sample.iloc[:, 1] if self.label_col is None else sample[self.label_col]
        scores = sample.iloc[:, 0] if self.score_col is None else sample[self.score_col]
        labels = np.stack(labels.values)
        scores = np.stack(scores.values)

        if self.average == "macro":
            return macro_auc(scores, labels)
        return micro_auc(scores, labels)


class ClassificationReportCalculator(BaseDriftCalculator):
    name = "class_report"

    def __init__(self, ref=None, label_col=None, score_col=None, target_names=None, th=0.5):
        super().__init__(None)

        self.label_col = label_col
        self.score_col = score_col
        self.target_names = target_names
        self.th = th

    def _predict(self, sample):
        labels = sample.iloc[:, 1] if self.label_col is None else sample[self.label_col]
        scores = sample.iloc[:, 0] if self.score_col is None else sample[self.score_col]

        labels = np.stack(labels.values)
        scores = np.stack(scores.values)

        return classification_report(scores, labels, target_names=self.target_names, th=self.th)
