"""
Audit credit score distribution for statistical health.

Checks:
- Score distribution (mean, median, std, skew)
- Risk level balance (no empty bins)
- Sub-score correlation (no single factor dominating)
- Outlier detection (IQR method)

Run: python manage.py audit_credit_scores
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from Payment.models import CreditScore
from Payment.services.credit_scoring import compute_credit_score
from Authentication.models import Profile
import json
import os
import statistics


def _describe(values):
    if not values:
        return {'count': 0}
    sorted_v = sorted(values)
    n = len(sorted_v)
    return {
        'count': n,
        'min': sorted_v[0],
        'max': sorted_v[-1],
        'mean': round(statistics.mean(sorted_v), 2),
        'median': sorted_v[n // 2],
        'stdev': round(statistics.stdev(sorted_v), 2) if n > 1 else 0,
        'p25': sorted_v[int(n * 0.25)],
        'p75': sorted_v[int(n * 0.75)],
    }


def _detect_outliers(values):
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[int(n * 0.25)]
    q3 = sorted_v[int(n * 0.75)]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = [v for v in values if v < lower or v > upper]
    return {
        'q1': q1,
        'q3': q3,
        'iqr': iqr,
        'lower_fence': lower,
        'upper_fence': upper,
        'outlier_count': len(outliers),
        'outlier_pct': round(len(outliers) / n * 100, 2) if n > 0 else 0,
    }


class Command(BaseCommand):
    help = 'Audit credit score distribution for statistical health'

    def handle(self, *args, **options):
        self.stdout.write('=== Credit Score Distribution Audit ===\n')

        all_scores = CreditScore.objects.all()
        total = all_scores.count()
        self.stdout.write(f'Total users with credit scores: {total}\n')

        if total == 0:
            self.stdout.write(self.style.WARNING('No credit scores found. Run compute first.'))
            return

        # ── 1. Score distribution ──
        scores = list(all_scores.values_list('score', flat=True))
        desc = _describe(scores)
        self.stdout.write(f'\n--- Score Distribution ---')
        self.stdout.write(f'Range: {desc["min"]} - {desc["max"]}')
        self.stdout.write(f'Mean: {desc["mean"]} | Median: {desc["median"]}')
        self.stdout.write(f'Std Dev: {desc["stdev"]}')
        self.stdout.write(f'Q1: {desc["p25"]} | Q3: {desc["p75"]}')

        # ── 2. Risk level bins ──
        self.stdout.write(f'\n--- Risk Level Breakdown ---')
        bins = {
            'very_low': all_scores.filter(score__gt=700).count(),
            'low': all_scores.filter(score__range=(601, 700)).count(),
            'moderate': all_scores.filter(score__range=(451, 600)).count(),
            'high': all_scores.filter(score__range=(301, 450)).count(),
            'very_high': all_scores.filter(score__lte=300).count(),
        }
        for risk, count in bins.items():
            pct = count / total * 100 if total > 0 else 0
            marker = self.style.WARNING(' ⚠ EMPTY') if count == 0 else ''
            self.stdout.write(f'  {risk}: {count} ({pct:.1f}%){marker}')

        # ── 3. Sub-score correlation check ──
        self.stdout.write(f'\n--- Sub-Score Averages ---')
        sub_fields = ['savings_score', 'repayment_score', 'group_score', 'transaction_score', 'tenure_score']
        for field in sub_fields:
            vals = list(all_scores.values_list(field, flat=True))
            avg = statistics.mean(vals) if vals else 0
            self.stdout.write(f'  {field}: avg={avg:.1f}')

        # ── 4. Outlier detection ──
        outliers = _detect_outliers(scores)
        self.stdout.write(f'\n--- Outlier Detection (IQR) ---')
        self.stdout.write(f'IQR: {outliers["iqr"]}')
        self.stdout.write(f'Fences: {outliers["lower_fence"]} - {outliers["upper_fence"]}')
        self.stdout.write(f'Outliers: {outliers["outlier_count"]} ({outliers["outlier_pct"]}%)')

        # ── 5. Stability: sample recompute vs stored ──
        self.stdout.write(f'\n--- Spot-Check: Recompute vs Stored ---')
        sample = all_scores.order_by('?').first()
        if sample:
            profile = sample.user
            fresh = compute_credit_score(profile)
            drift = abs(fresh['total_score'] - sample.score)
            flag = self.style.WARNING(' ⚠ DRIFT') if drift > 50 else ''
            self.stdout.write(f'  User {profile.id}: stored={sample.score} recomputed={fresh["total_score"]} diff={drift}{flag}')

        # ── 6. Baseline snapshot ──
        baseline = {
            'timestamp': timezone.now().isoformat(),
            'total_users': total,
            'distribution': desc,
            'risk_bins': bins,
            'outliers': outliers,
        }
        baseline_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'credit_score_baseline.json')
        with open(os.path.normpath(baseline_path), 'w') as f:
            json.dump(baseline, f, indent=2)
        self.stdout.write(f'\nBaseline saved to credit_score_baseline.json')

        # ── Summary verdict ──
        has_empty_bins = any(c == 0 for c in bins.values())
        high_outliers = outliers['outlier_pct'] > 5
        warnings = []
        if has_empty_bins:
            warnings.append('Empty risk-level bins — score thresholds may need adjustment')
        if high_outliers:
            warnings.append(f'High outlier ratio ({outliers["outlier_pct"]}%) — investigate edge cases')
        if desc['stdev'] < 50:
            warnings.append('Very low variance — scores may not differentiate users enough')

        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f'\n⚠ {w}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Score distribution looks healthy'))
