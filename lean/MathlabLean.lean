import Mathlib.Tactic
import MathlabLean.OddSum

/-! Library root. `lake build` checks every module listed here at image build time.

* smoke test of the container (F-00.04): Mathlib loads and a tactic proof checks,
* `MathlabLean.OddSum`: the sum-of-odd-numbers example of ARCH §15 (F-04.01).
-/

theorem mathlab_smoke (n : Nat) : 2 * n = n + n := by omega

example : (2 : ℚ) + 2 = 4 := by norm_num
