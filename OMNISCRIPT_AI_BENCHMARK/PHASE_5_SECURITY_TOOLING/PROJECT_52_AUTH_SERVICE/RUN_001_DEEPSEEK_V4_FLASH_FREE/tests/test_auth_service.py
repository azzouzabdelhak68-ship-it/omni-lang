# Authenticated Web Service Tests — Project 5.2 (RUN_001_DEEPSEEK_V4_FLASH_FREE)
# Automated suite verifying compiler acceptance, secrets capability declarations,
# and runtime registration/login/token/authorization flows.

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
SOURCE_FILE = PROJECT_DIR / "source" / "auth_service.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


def run_omni(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run an omni CLI command and return the result."""
    return subprocess.run(
        OMNI_CLI + command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


def build_emitted_html() -> str:
    """Build the JS target and return the emitted HTML source."""
    with tempfile.TemporaryDirectory(dir=PROJECT_DIR) as tmp:
        out = Path(tmp) / "auth_service.html"
        result = run_omni(["build", str(SOURCE_FILE), "-o", str(out)])
        assert result.returncode == 0, f"build failed: {result.stderr}"
        assert out.exists(), f"build artifact missing: {out}"
        return out.read_text(encoding="utf-8")


def run_emitted(html: str, epilogue: str) -> subprocess.CompletedProcess[str]:
    """Run an emitted HTML document under Node with a DOM stub + epilogue.

    Top-level emitted functions attach to globalThis (vm.runInThisContext), so
    the epilogue can call svc_* / endpoint_* directly and report JSON through
    a log line prefixed with `__OUT__`.
    """
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.error("no script block"); process.exit(2); }
const code = match[1];
global.__logs = [];
global.console = Object.assign({}, console, {
  log: (...a) => global.__logs.push(a.map(String).join(" ")),
});
global.__app = { innerHTML: "", addEventListener: (t, fn) => { global.__listener = fn; } };
global.document = {
  getElementById: () => global.__app,
  querySelectorAll: () => [],
  createElement: () => ({}),
  head: { appendChild() {} },
  body: { appendChild() {} },
};
global.window = global;
vm.runInThisContext(code, { filename: htmlPath });
"""
    runner_src = (
        harness
        + epilogue
        + '\nprocess.stdout.write(JSON.stringify(global.__logs) + "\\n");\n'
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", encoding="utf-8", delete=False
    ) as f:
        f.write(html)
        html_path = Path(f.name)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", encoding="utf-8", delete=False
    ) as g:
        g.write(runner_src)
        runner_path = Path(g.name)
    try:
        return subprocess.run(
            ["node", str(runner_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        html_path.unlink(missing_ok=True)
        runner_path.unlink(missing_ok=True)


def parse_output(proc: subprocess.CompletedProcess[str]) -> dict:
    """Extract the `__OUT__` record from the harness log output."""
    assert proc.returncode == 0, (
        f"runtime failed (rc={proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    logs = json.loads(proc.stdout)
    for line in logs:
        if line.startswith("__OUT__"):
            return json.loads(line[len("__OUT__") :])
    pytest.fail(f"no __OUT__ record found in runtime logs: {logs!r}")


# --- Compiler acceptance tests -------------------------------------------------


class TestCompilerChecks:
    """omni check / build / verify acceptance."""

    def test_check_passes(self):
        """omni check source/auth_service.omni exits with code 0."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Compiler check failed: {result.stderr}"

    def test_build_succeeds(self):
        """omni build emits the JS target artifact."""
        with tempfile.TemporaryDirectory(dir=PROJECT_DIR) as tmp:
            out = Path(tmp) / "auth_service.html"
            result = run_omni(["build", str(SOURCE_FILE), "-o", str(out)])
            assert result.returncode == 0, f"Build failed: {result.stderr}"
            assert out.exists() and out.stat().st_size > 0

    def test_verify_all_contracts_proven(self):
        """omni verify reports only verified or no-contracts."""
        result = run_omni(["verify", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Verify failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["schema"] == "omni.verify.batch"
        assert len(data["results"]) >= 9  # 9 service functions
        for fn_result in data["results"]:
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )


# --- Capability declaration tests ----------------------------------------------


class TestCapabilityDeclarations:
    """Every auth/crypto boundary declares `uses secrets`."""

    SECRETS_FUNCTIONS = [
        "svc_register",
        "svc_issue_token",
        "svc_login",
        "svc_verify",
        "svc_logout",
        "endpoint_profile",
        "endpoint_admin",
        "svc_start_session",
        "svc_session_status",
    ]

    @pytest.mark.parametrize("fn_name", SECRETS_FUNCTIONS)
    def test_secrets_declared(self, fn_name):
        """Function declares `uses secrets` (reported by omni inspect)."""
        result = run_omni(["inspect", fn_name, str(SOURCE_FILE)])
        assert result.returncode == 0, f"inspect {fn_name} failed: {result.stderr}"
        data = json.loads(result.stdout)
        uses = data.get("declared_effects", {}).get("uses", [])
        assert "secrets" in uses, f"{fn_name} does not declare secrets: {uses}"

    def test_passwords_not_plaintext_in_demo(self):
        """Emitted program never stores plaintext passwords (demo run output)."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"run failed: {result.stderr}"
        assert "correct-horse" not in result.stdout.split("hash")[-1].split("store")[0]
        assert '"hash"' in result.stdout


# --- Runtime behavioral tests --------------------------------------------------


class TestRuntimeBehavior:
    """Register -> login -> token issue -> verify flows, executed under Node."""

    EPILOGUE = r"""
const store0 = {__revoked__: []};
const secret = "benchmark-secret-key-001";
const reg = svc_register(store0, "tester", "hunter2", "user");
const dup = svc_register(reg.store, "tester", "another", "user");
const regBoss = svc_register(reg.store, "boss", "s3cret", "admin");
const loginOk = svc_login(regBoss.store, "tester", "hunter2", secret, 3600);
const loginBoss = svc_login(regBoss.store, "boss", "s3cret", secret, 3600);
const loginBadPw = svc_login(regBoss.store, "tester", "wrong-password", secret, 3600);
const loginUnknown = svc_login(regBoss.store, "nobody", "x", secret, 3600);
const verifyOk = svc_verify(regBoss.store, secret, loginOk.token);
const staleTok = svc_issue_token(secret, "tester", "user", -5);
const verifyExpired = svc_verify(regBoss.store, secret, staleTok);
const verifyTampered = svc_verify(regBoss.store, secret, "not.a.real.token");
const profOk = endpoint_profile(regBoss.store, secret, loginOk.token);
const profAnon = endpoint_profile(regBoss.store, secret, "bad.token");
const adminBoss = endpoint_admin(regBoss.store, secret, loginBoss.token);
const adminUser = endpoint_admin(regBoss.store, secret, loginOk.token);
const logout = svc_logout(regBoss.store, secret, loginOk.token);
const verifyRevoked = svc_verify(logout.store, secret, loginOk.token);
const session = svc_start_session(secret, "tester", 3600);
const sessionStatus = svc_session_status(session);
const sessionExpired = svc_session_status(svc_start_session(secret, "tester", -1));
global.__out = {
  register: {ok: reg.ok, status: reg.status, message: reg.message},
  duplicate: {ok: dup.ok, status: dup.status},
  loginOk: {ok: loginOk.ok, status: loginOk.status, hasToken: typeof loginOk.token === "string" && loginOk.token.length > 10},
  loginBadPw: {ok: loginBadPw.ok, status: loginBadPw.status},
  loginUnknown: {ok: loginUnknown.ok, status: loginUnknown.status},
  verifyOk: {ok: verifyOk.ok, subject: verifyOk.subject},
  verifyExpired: {ok: verifyExpired.ok, message: verifyExpired.message},
  verifyTampered: {ok: verifyTampered.ok, message: verifyTampered.message},
  verifyRevoked: {ok: verifyRevoked.ok, message: verifyRevoked.message},
  profileOk: {ok: profOk.ok, status: profOk.status, message: profOk.message},
  profileAnon: {ok: profAnon.ok, status: profAnon.status},
  adminBoss: {ok: adminBoss.ok, status: adminBoss.status, message: adminBoss.message},
  adminUser: {ok: adminUser.ok, status: adminUser.status},
  sessionStatus: sessionStatus,
  sessionExpired: sessionExpired,
};
global.__logs.push("__OUT__" + JSON.stringify(global.__out));
"""

    @needs_node
    def test_registration_and_duplicate_rejected(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["register"]["ok"] is True
        assert out["register"]["status"] == 201
        assert out["duplicate"]["ok"] is False
        assert out["duplicate"]["status"] == 409

    @needs_node
    def test_login_issues_token(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["loginOk"]["ok"] is True
        assert out["loginOk"]["status"] == 200
        assert out["loginOk"]["hasToken"] is True

    @needs_node
    def test_wrong_password_rejected(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["loginBadPw"]["ok"] is False
        assert out["loginBadPw"]["status"] == 401

    @needs_node
    def test_unknown_user_rejected(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["loginUnknown"]["ok"] is False
        assert out["loginUnknown"]["status"] == 401

    @needs_node
    def test_token_verify_round_trip(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["verifyOk"]["ok"] is True
        assert out["verifyOk"]["subject"] == "tester"

    @needs_node
    def test_expired_token_rejected(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["verifyExpired"]["ok"] is False
        assert "expired" in out["verifyExpired"]["message"]

    @needs_node
    def test_tampered_token_rejected(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["verifyTampered"]["ok"] is False

    @needs_node
    def test_logout_revokes_token(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["verifyRevoked"]["ok"] is False
        assert "revoked" in out["verifyRevoked"]["message"]

    @needs_node
    def test_protected_endpoint_authorizes_authenticated(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["profileOk"]["ok"] is True
        assert out["profileOk"]["status"] == 200

    @needs_node
    def test_protected_endpoint_rejects_unauthenticated(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["profileAnon"]["ok"] is False
        assert out["profileAnon"]["status"] == 401

    @needs_node
    def test_role_based_access_control(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        # admin-role holder is granted
        assert out["adminBoss"]["ok"] is True
        assert out["adminBoss"]["status"] == 200
        # non-admin role is denied with 403
        assert out["adminUser"]["ok"] is False
        assert out["adminUser"]["status"] == 403

    @needs_node
    def test_session_validity(self):
        html = build_emitted_html()
        out = parse_output(run_emitted(html, self.EPILOGUE))
        assert out["sessionStatus"] == "session valid"
        assert out["sessionExpired"] == "session expired"


# --- Demo smoke test ------------------------------------------------------------


class TestDemoRun:
    """The entry-block demo executes end to end under Node."""

    @needs_node
    def test_demo_run_exit_zero(self):
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"demo run failed: {result.stderr}"

    @needs_node
    def test_demo_covers_all_flows(self):
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0
        stdout = result.stdout
        for fragment in [
            '"status":201',  # registered
            '"status":409',  # duplicate
            '"message":"authenticated"',  # login ok
            '"wrong password"',  # bad password
            '"unknown user"',  # unknown user
            '"profile for alice"',  # protected endpoint ok
            '"unauthorized: invalid signature"',  # anon rejected
            '"admin access granted"',  # role ok
            '"forbidden: admin role required"',  # role denied
            '"token expired"',  # expiry rejection
            '"token revoked"',  # logout revocation
            "session valid",
            "session expired",
        ]:
            assert fragment in stdout, f"demo output missing: {fragment!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])