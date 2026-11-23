import Mathlib.Tactic

/-! Smoke test for the container (F-00.04): Mathlib loads and a tactic proof checks. -/

theorem mathlab_smoke (n : Nat) : 2 * n = n + n := by omega

example : (2 : ℚ) + 2 = 4 := by norm_num
