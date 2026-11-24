import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Tactic

/-! Sum of odd numbers, the worked example of ARCH §15 (F-04.01).

`odd_sum` states ARCH §15 literally: for `n ≥ 1`, `∑_{k=1}^{n} (2k - 1) = n²`. The statement
also holds for `n = 0` (empty sum), so the hypothesis is not needed. Natural-number subtraction
is exact here because `k ≥ 1` on `Icc 1 n`. `odd_sum_range` is the 0-indexed form used by the
inductive proof of §15.3.
-/

namespace MathlabLean

/-- Inductive proof (ARCH §15.3): `∑_{k<n} (2k + 1) = n²`. -/
theorem odd_sum_range (n : ℕ) : ∑ k ∈ Finset.range n, (2 * k + 1) = n ^ 2 := by
  induction n with
  | zero => simp
  | succ n ih => rw [Finset.sum_range_succ, ih]; ring

/-- ARCH §15: `∑_{k=1}^{n} (2k - 1) = n²` for `n ≥ 1`. -/
theorem odd_sum (n : ℕ) (_hn : 1 ≤ n) : ∑ k ∈ Finset.Icc 1 n, (2 * k - 1) = n ^ 2 := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Finset.sum_Icc_succ_top (by omega)]
    rcases Nat.eq_zero_or_pos n with rfl | hpos
    · simp
    · rw [ih hpos, show 2 * (n + 1) - 1 = 2 * n + 1 by omega]; ring

end MathlabLean
