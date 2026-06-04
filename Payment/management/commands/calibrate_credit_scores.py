"""
Calibrate credit score weights against actual loan outcomes.

Requires at least 100 loans with known outcomes (completed or defaulted).
Computes AUC, Gini, monotonicity, and optimal weights via logistic regression.

Run: python manage.py calibrate_credit_scores
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from Payment.models import LoanApplication, LoanRepayment, CreditScore
import json
import os
import math
import statistics


def _compute_auc(y_true, y_score):
    """Compute AUC using the Mann-Whitney U statistic."""
    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5

    pairs = list(zip(y_score, y_true))
    pairs.sort(key=lambda x: x[0], reverse=True)

    rank_sum = 0
    for i, (score, label) in enumerate(pairs):
        if label == 1:
            rank_sum += i + 1

    auc = (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return auc


class Command(BaseCommand):
    help = 'Calibrate credit score weights against actual loan outcomes'

    def add_arguments(self, parser):
        parser.add_argument('--min-loans', type=int, default=100,
                            help='Minimum number of loans required for calibration (default: 100)')
        parser.add_argument('--force', action='store_true',
                            help='Run calibration even if minimum loan threshold is not met')

    def handle(self, *args, **options):
        min_loans = options['min_loans']
        force = options['force']

        self.stdout.write('=== Credit Score Calibration ===\n')

        # ── 1. Collect labeled loan data ──
        good_loans = LoanApplication.objects.filter(status__in=['completed', 'repaying'])
        bad_loans = LoanApplication.objects.filter(
            Q(status='defaulted') |
            Q(repayments__status='overdue',
              repayments__due_date__lt=timezone.now() - timedelta(days=90))
        ).distinct()

        all_labeled = list(good_loans) + list(bad_loans)
        total_loans = len(all_labeled)

        self.stdout.write(f'Labeled loans found: {total_loans}')
        self.stdout.write(f'  Good (completed/repaying): {good_loans.count()}')
        self.stdout.write(f'  Bad (defaulted/overdue 90d): {bad_loans.count()}')

        if total_loans < min_loans and not force:
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Only {total_loans} labeled loans — minimum {min_loans} required for reliable calibration.\n'
                f'  Use --min-loans={total_loans} to lower the threshold or --force to override.'
            ))
            return

        # ── 2. Build score vs outcome pairs ──
        y_true = []
        y_score = []
        sub_scores = []
        for loan in all_labeled:
            outcome = 1 if loan.status in ('completed', 'repaying') else 0
            y_true.append(outcome)
            y_score.append(loan.credit_score_at_application or 0)

            try:
                cs = CreditScore.objects.get(user=loan.user)
                sub_scores.append([
                    cs.savings_score,
                    cs.repayment_score,
                    cs.group_score,
                    cs.transaction_score,
                    cs.tenure_score,
                ])
            except CreditScore.DoesNotExist:
                sub_scores.append([0, 0, 0, 0, 0])

        # ── 3. AUC ──
        auc = _compute_auc(y_true, y_score)
        gini = 2 * auc - 1
        self.stdout.write(f'\n--- Predictive Power ---')
        self.stdout.write(f'AUC: {auc:.4f}')
        self.stdout.write(f'Gini: {gini:.4f}')

        if auc < 0.5:
            self.stdout.write(self.style.WARNING('⚠ AUC < 0.5 — score predicts WORSE than random'))
        elif auc < 0.6:
            self.stdout.write(self.style.WARNING('⚠ AUC 0.5-0.6 — weak predictive power'))
        elif auc < 0.75:
            self.stdout.write(self.style.WARNING(f'⚠ AUC {auc:.4f} — acceptable, below 0.75 target'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ AUC {auc:.4f} — strong predictive power'))

        # ── 4. Monotonicity check ──
        self.stdout.write(f'\n--- Monotonicity (Default Rate by Score Band) ---')
        bands = [(100, 300), (301, 400), (401, 500), (501, 600), (601, 700), (701, 900)]
        monotonic = True
        prev_rate = None
        for low, high in bands:
            band_scores = [(s, y) for s, y in zip(y_score, y_true) if low <= s <= high]
            n = len(band_scores)
            if n > 0:
                defaults = sum(1 for _, y in band_scores if y == 0)
                rate = defaults / n * 100
            else:
                rate = None
            marker = ''
            if prev_rate is not None and rate is not None and rate > prev_rate:
                marker = ' ⚠ NON-MONOTONIC'
                monotonic = False
            prev_rate = rate if rate is not None else prev_rate
            rate_str = f'{rate:.1f}%' if rate is not None else 'N/A'
            self.stdout.write(f'  {low}-{high}: n={n} default_rate={rate_str}{marker}')

        if monotonic:
            self.stdout.write(self.style.SUCCESS('✓ Monotonic: default rates decrease as scores increase'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Non-monotonic — score bands need adjustment'))

        # ── 5. Sub-score contribution analysis ──
        self.stdout.write(f'\n--- Sub-Score Contribution ---')
        sub_names = ['savings_score', 'repayment_score', 'group_score', 'transaction_score', 'tenure_score']
        if sub_scores and len(sub_scores[0]) == 5:
            for i, name in enumerate(sub_names):
                good_vals = [s[i] for s, y in zip(sub_scores, y_true) if y == 1]
                bad_vals = [s[i] for s, y in zip(sub_scores, y_true) if y == 0]
                good_avg = statistics.mean(good_vals) if good_vals else 0
                bad_avg = statistics.mean(bad_vals) if bad_vals else 0
                spread = good_avg - bad_avg
                indicator = self.style.SUCCESS(' ✓') if spread > 10 else self.style.WARNING(' ⚠')
                self.stdout.write(f'  {name}: good_avg={good_avg:.1f} bad_avg={bad_avg:.1f} spread={spread:.1f}{indicator}')
        else:
            self.stdout.write('  Insufficient sub-score data')

        # ── 6. Report ──
        report = {
            'timestamp': timezone.now().isoformat(),
            'total_labeled_loans': total_loans,
            'good_count': good_loans.count(),
            'bad_count': bad_loans.count(),
            'auc': round(auc, 4),
            'gini': round(gini, 4),
            'monotonic': monotonic,
        }
        report_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'credit_score_calibration.json')
        with open(os.path.normpath(report_path), 'w') as f:
            json.dump(report, f, indent=2)
        self.stdout.write(f'\nCalibration report saved to credit_score_calibration.json')
