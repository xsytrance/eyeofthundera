# Fixtures for the worked examples

`file0_pacifist` and `undertale_pacifist.ini` are a minimal Undertale save,
copied from `undertale-vera/tests/fixtures/`. They are **synthetic** — that
repo's `tools/make_synthetic_fixtures.py` exists precisely because the original
corpus carried a real player's name. Nothing here is anyone's data.

They exist so `examples/undertale-vera.toml` can demonstrate an `upload` setup
step against a real precondition, and so `thundera check` on that example
passes in CI: a missing upload fixture is a config error by design.
