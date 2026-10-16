import json
import os
from pathlib import Path
import pty
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pi-search ' $ ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.home = self.work / "home"
        self.home.mkdir()
        self.bin = self.work / "bin"
        self.bin.mkdir()
        for name in ("awk", "bash", "basename", "cat", "chmod", "cut", "date", "dirname",
                     "find", "grep", "head", "jq", "mkdir", "mv", "rg", "rm", "sed",
                     "sort", "stat", "tr"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.log = self.work / "commands.jsonl"
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin),
                        SHELL="/bin/bash", COMMAND_LOG=str(self.log),
                        FIXTURE_ROOT=str(ROOT), FZF_CAPTURE=str(self.work / "fzf.json"))
        self.env.pop("PI_SEARCH_EDITOR", None)

    def mock(self, name, body=""):
        path = self.bin / name
        if path.is_symlink():
            path.unlink()
        path.write_text(
            f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
            "with Path(os.environ['COMMAND_LOG']).open('a') as log:\n"
            " log.write(json.dumps({'tool':Path(sys.argv[0]).name,'args':sys.argv[1:],"
            "'cwd':os.getcwd(),'query':os.environ.get('NVIM_QUERY')})+'\\n')\n" + body
        )
        path.chmod(0o755)
        return path

    def commands(self, name):
        return [row for row in map(json.loads, self.log.read_text().splitlines())
                if row["tool"] == name] if self.log.exists() else []

    def run_command(self, argv, *, tty=False, picker=False, cwd=None):
        master = slave = None
        if tty or picker:
            master, slave = pty.openpty()
        try:
            return subprocess.run(argv, env=self.env, cwd=cwd, timeout=15,
                                  stdin=slave if picker else subprocess.DEVNULL,
                                  stdout=slave if tty else subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        finally:
            if slave is not None:
                os.close(slave)
                os.close(master)

    def cli(self, *args, **kwargs):
        return self.run_command([str(ROOT / "pi-search"), *map(str, args)], **kwargs)

    def check_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def session(self, name="parent", messages=None, cwd=None):
        source = self.home / ".pi/agent/sessions/--repo--" / f"{name}.jsonl"
        source.parent.mkdir(parents=True, exist_ok=True)
        rows = [{"type": "session", "version": 3, "id": name, "cwd": str(cwd or self.work)}]
        for role, content in messages or [("assistant", "redis")]:
            if isinstance(content, list):
                content = [{"type": "text", "text": text} for text in content]
            rows.append({"type": "message", "message": {"role": role, "content": content}})
        source.write_text("".join(json.dumps(row) + "\n" for row in rows))
        return source

    def markdown(self, source, full=False):
        rel = source.relative_to(self.home / ".pi/agent/sessions").with_suffix(".md")
        return self.home / (".pi/agent/sessions-md-full" if full else ".pi/agent/sessions-md") / rel

    def transcript(self):
        path = self.home / ".pi/agent/sessions-md/--repo--/fixture.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"line {i}\n" for i in range(1, 11)))
        return path

    def qmd(self):
        self.mock("qmd", """
args = sys.argv[1:]
if args == ['collection', 'list']:
 if os.environ.get('COLLECTION_EXISTS'): print('pi-history (qmd://pi-history/)')
elif args[0] in ('update', 'embed') or args[:2] == ['collection', 'add']:
 corpus = Path(os.environ['HOME']) / '.pi/agent/sessions-md'
 assert corpus.is_dir(), 'corpus must exist before indexing'
 if os.environ.get('EXPECT_EXPORTED'): assert list(corpus.rglob('*.md')), 'export before indexing'
elif args[0] == 'vsearch':
 rows = json.loads(Path(os.environ['SEMANTIC_FIXTURE']).read_text())
 if '--all' not in args: rows = rows[:int(args[args.index('-n')+1])]
 print(json.dumps(rows))
elif args[0] == 'status': print('Updated: fixture')
else: raise AssertionError(args)
""")

    def test_export_preserves_cwd_metacharacters_and_complete_text(self):
        cwd = self.work / "R&D|project"
        cwd.mkdir()
        source = self.session(messages=[("assistant", ["x" * 2100 + "bodyneedle"]),
                                        ("toolResult", ["x" * 250 + "toolneedle"]),
                                        ("user", "stringneedle"),
                                        ("user", "<html>stringhtml</html>"),
                                        ("assistant", ["<!DOCTYPE html>arrayhtml"])], cwd=cwd)
        self.check_ok(self.cli("export"))
        lean = self.markdown(source).read_text()
        self.assertEqual(lean.splitlines()[0], f"_session cwd: {cwd}_")
        self.assertIn("bodyneedle", lean)
        self.assertIn("stringneedle", lean)
        for excluded in ("toolneedle", "stringhtml", "arrayhtml", "[truncated]"):
            self.assertNotIn(excluded, lean)
        self.check_ok(self.cli("bodyneedle"))
        self.check_ok(self.cli("-t", "toolneedle"))
        full = self.markdown(source, full=True).read_text()
        self.assertIn("bodyneedle", full)
        self.assertIn("toolneedle", full)
        self.assertNotIn("stringhtml", full)
        self.assertNotIn("arrayhtml", full)

    def test_incremental_export_and_invalid_source_preserve_transcript(self):
        source = self.session()
        self.check_ok(self.cli("export"))
        output = self.markdown(source)
        before = output.stat().st_mtime_ns
        self.check_ok(self.cli("export"))
        self.assertEqual(output.stat().st_mtime_ns, before)
        expected = output.read_text()
        source.write_text(source.read_text() + "invalid json\n")
        os.utime(source, (time.time() + 5, time.time() + 5))
        self.check_ok(self.cli("export"))
        self.assertEqual(output.read_text(), expected)
        self.assertFalse(output.with_suffix(".md.body").exists())

    def test_html_only_session_removes_stale_export(self):
        source = self.session()
        self.check_ok(self.cli("export"))
        output = self.markdown(source)
        self.assertTrue(output.exists())
        self.session(messages=[("assistant", "<html>hidden</html>")])
        os.utime(source, (time.time() + 5, time.time() + 5))
        self.check_ok(self.cli("export"))
        self.assertFalse(output.exists())

    def test_exporter_update_invalidates_old_cache(self):
        source = self.session()
        self.check_ok(self.cli("export"))
        output = self.markdown(source)
        stamp = (ROOT / "pi-export-history").stat().st_mtime - 100
        output.write_text("old truncated export")
        os.utime(source, (stamp - 10, stamp - 10))
        os.utime(output, (stamp, stamp))
        self.check_ok(self.cli("export"))
        self.assertIn("redis", output.read_text())

    def test_keyword_ties_keep_session_hit_rank(self):
        parent = self.session(messages=[("assistant", "redis redis\nredis")])
        other = self.session("other")
        rows = self.check_ok(self.cli("--all", "redis")).splitlines()
        paths = [row.split("\t")[1] for row in rows]
        self.assertEqual(paths, ["--repo--/parent.md", "--repo--/parent.md", "--repo--/other.md"])
        self.assertTrue(self.markdown(parent).exists() and self.markdown(other).exists())

    def test_resume_lean_full_and_relative_transcripts(self):
        source = self.session()
        self.mock("pi")
        self.check_ok(self.cli("export"))
        self.check_ok(self.cli("export", "-t"))
        for full in (False, True):
            path = self.markdown(source, full)
            self.check_ok(self.cli("resume", path))
            self.check_ok(self.cli("resume", path.relative_to(self.home), cwd=self.home))
        for call in self.commands("pi"):
            self.assertEqual(call["args"], ["--session", str(source)])
            self.assertEqual(call["cwd"], str(self.work.resolve()))

    def test_picker_enter_resumes_and_ctrl_o_opens(self):
        source = self.session()
        self.mock("pi")
        self.mock("bat")
        self.mock("editor")
        self.mock("fzf", """
assert '--expect=ctrl-o' in sys.argv
assert any('enter: resume · ctrl-o: open' in arg for arg in sys.argv)
assert not any('ctrl-v' in arg for arg in sys.argv)
rows = sys.stdin.read().splitlines()
print(os.environ['FZF_KEY'])
print(rows[0])
""")
        self.qmd()
        fixture = self.work / "semantic.json"
        fixture.write_text(json.dumps([{"file": "qmd://pi-history/--repo--/parent.md",
                                        "line": 5, "score": .8, "snippet": "redis"}]))
        self.env["SEMANTIC_FIXTURE"] = str(fixture)
        for editor in (None, "editor --fixture"):
            if editor is None:
                self.env.pop("PI_SEARCH_EDITOR", None)
            else:
                self.env["PI_SEARCH_EDITOR"] = editor
            for args in (("-p", "redis"), ("-p", "-t", "redis"), ("-v", "-p", "redis")):
                for key, tool in (("", "pi"), ("ctrl-o", "editor" if editor else "bat")):
                    with self.subTest(editor=editor, args=args, key=key):
                        before = {name: len(self.commands(name)) for name in ("pi", "bat", "editor")}
                        self.env["FZF_KEY"] = key
                        self.check_ok(self.cli(*args, picker=True))
                        for name in before:
                            self.assertEqual(len(self.commands(name)), before[name] + (name == tool))
                        call = self.commands(tool)[-1]
                        transcript = str(self.markdown(source, full="-t" in args))
                        if key == "":
                            self.assertEqual(call["args"], ["--session", str(source)])
                        elif editor:
                            self.assertEqual(call["args"], ["--fixture", transcript])
                        else:
                            self.assertEqual(call["args"][-1], transcript)
                            self.assertIn("--highlight-line", call["args"])
        self.mock("editor", "sys.exit(7)\n")
        before = len(self.commands("bat"))
        self.assertEqual(self.cli("-p", "redis", picker=True).returncode, 7)
        self.assertEqual(len(self.commands("bat")), before)
        self.assertNotIn("ctrl-v", self.check_ok(self.cli("--help")))

    def test_piped_show_uses_bat_and_not_nvim(self):
        path = self.transcript()
        self.mock("nvim")
        self.mock("bat")
        self.check_ok(self.cli("show", path, 3, "redis"))
        self.assertEqual(self.commands("nvim"), [])
        self.assertIn("--paging=auto", self.commands("bat")[0]["args"])

    def test_show_and_preview_without_optional_viewers(self):
        path = self.transcript()
        self.assertEqual(self.check_ok(self.cli("show", path, 3)), path.read_text())
        self.assertEqual(self.check_ok(self.cli("--preview", path, 7)),
                         "".join(f"line {i}\n" for i in range(2, 11)))

    def test_interactive_show_falls_back_to_bat_then_less(self):
        path = self.transcript()
        bat = self.mock("bat")
        self.check_ok(self.cli("show", path, 3, tty=True))
        self.assertEqual(len(self.commands("bat")), 1)
        bat.unlink()
        self.mock("less")
        self.check_ok(self.cli("show", path, 3, tty=True))
        self.assertEqual(self.commands("less")[0]["args"], ["-R", "+3", str(path)])

    def test_nvim_uses_case_insensitive_literal_highlighting(self):
        path = self.transcript()
        self.mock("nvim")
        self.check_ok(self.cli("show", path, 3, r"Redis\timeout", tty=True))
        call = self.commands("nvim")[0]
        self.assertEqual(call["query"], r"Redis\timeout")
        self.assertIn(r"\\c\\V", " ".join(call["args"]))
        self.assertIn("normal! 3zz", call["args"])

    def test_preview_prefers_bat_if_available(self):
        path = self.transcript()
        self.mock("bat")
        self.check_ok(self.cli("--preview", path, 7))
        args = self.commands("bat")[0]["args"]
        self.assertIn("--paging=never", args)
        self.assertIn("2:", args)
        self.assertIn("--highlight-line=7", args)

    def test_non_timestamped_age_uses_source_mtime(self):
        source = self.session()
        stamp = time.time() - 3610
        os.utime(source, (stamp, stamp))
        self.assertIn("1h ago", self.check_ok(self.cli("redis")))

    def test_gnu_stat_and_date_paths(self):
        self.session()
        self.mock("stat", "assert sys.argv[1] == '-c'\nprint(1000000)\n")
        self.mock("date", """
args = sys.argv[1:]
if args == ['+%s']: print(1003600)
elif args == ['-d', '@1000000', '+%Y-%m-%d']: print('1970-01-12')
else: raise AssertionError(args)
""")
        self.assertIn("1h ago", self.check_ok(self.cli("redis")))
        self.assertTrue(self.commands("stat"))

    def install(self, existing=False):
        self.session()
        self.mock("fzf")
        self.mock("curl", """
import shutil
url = sys.argv[2]
destination = sys.argv[sys.argv.index('-o')+1]
shutil.copyfile(Path(os.environ['FIXTURE_ROOT']) / url.rsplit('/',1)[1], destination)
""")
        self.qmd()
        self.env["EXPECT_EXPORTED"] = "1"
        if existing:
            self.env["COLLECTION_EXISTS"] = "1"
        destination = self.work / "custom install"
        self.env["PI_SEARCH_BIN"] = str(destination)
        self.check_ok(self.run_command(["/bin/sh", str(ROOT / "install.sh")]))
        return destination

    def test_fresh_install_exports_before_collection_and_embed(self):
        destination = self.install()
        calls = [row["args"] for row in self.commands("qmd")]
        self.assertEqual(calls[0], ["collection", "list"])
        self.assertEqual(calls[1][:2], ["collection", "add"])
        self.assertEqual(calls[2], ["embed", "-c", "pi-history"])
        self.assertTrue((destination / "pi-search").is_file())

    def test_existing_install_updates_collection_after_export(self):
        self.install(existing=True)
        self.assertEqual([row["args"] for row in self.commands("qmd")],
                         [["collection", "list"], ["update", "-c", "pi-history"],
                          ["embed", "-c", "pi-history"]])

    def test_custom_location_maintenance_initializes_and_prunes(self):
        source = self.session()
        self.qmd()
        destination = self.work / "custom install"
        destination.mkdir()
        for name in ("pi-search-maintenance", "pi-export-history"):
            shutil.copy2(ROOT / name, destination / name)
        command = [str(destination / "pi-search-maintenance")]
        self.check_ok(self.run_command(command))
        output = self.markdown(source)
        self.assertTrue(output.is_file())
        source.unlink()
        self.check_ok(self.run_command(command))
        self.assertFalse(output.exists())
        self.assertTrue((self.home / ".pi/agent/sessions-md").is_dir())

    def test_empty_home_export_and_maintenance(self):
        self.qmd()
        self.check_ok(self.cli("export"))
        shutil.rmtree(self.home / ".pi/agent/sessions-md")
        self.check_ok(self.run_command([str(ROOT / "pi-search-maintenance")]))
        self.assertTrue((self.home / ".pi/agent/sessions-md").is_dir())

    def test_picker_callbacks_work_without_pi_search_on_path(self):
        source = self.session("2020-01-01T00-00-00_parent")
        self.qmd()
        self.mock("fzf", """
Path(os.environ['FZF_CAPTURE']).write_text(json.dumps({'args':sys.argv[1:],'rows':sys.stdin.read()}))
sys.exit(1)
""")
        self.mock("pbcopy", "Path(os.environ['HOME']).joinpath('clipboard').write_text(sys.stdin.read())\n")
        self.mock("osascript")
        parent = "--repo--/2020-01-01T00-00-00_parent.md"
        child = "--repo--/subagent-artifacts/child.md"
        fixture = self.work / "semantic.json"
        fixture.write_text(json.dumps([
            {"file": "qmd://pi-history/" + file, "line": 3, "score": score, "snippet": "redis"}
            for file, score in [(child, .9), (parent, .8), (parent, .7)]
        ]))
        self.env["SEMANTIC_FIXTURE"] = str(fixture)
        checkout = self.work / "script directory"
        checkout.mkdir()
        for name in ("pi-search", "pi-export-history"):
            shutil.copy2(ROOT / name, checkout / name)
        self.check_ok(self.run_command([str(checkout / "pi-search"), "-v", "-p", "-d", "-n", "1", "redis"], picker=True))
        capture = json.loads(Path(self.env["FZF_CAPTURE"]).read_text())
        reload = next(arg for arg in capture["args"] if arg.startswith("--bind=ctrl-r:reload("))
        command = reload.removeprefix("--bind=ctrl-r:reload(").removesuffix(")")
        self.assertIn("-p", command)
        self.assertEqual(self.check_ok(self.run_command(["/bin/sh", "-c", command])), capture["rows"])
        self.assertEqual(len(capture["rows"].splitlines()), 1)
        self.assertNotIn(child, capture["rows"])
        for key in ("ctrl-x", "ctrl-t"):
            bind = next(arg for arg in capture["args"] if arg.startswith(f"--bind={key}:transform("))
            command = bind.split(":transform(", 1)[1].split(" >/dev/null", 1)[0]
            command = command.replace("{2}", shlex.quote(parent))
            self.check_ok(self.run_command(["/bin/sh", "-c", command]))
        transcript = str(self.markdown(source))
        self.assertEqual((self.home / "clipboard").read_text(), transcript)
        self.assertEqual(self.commands("osascript")[0]["args"][-1], transcript)
        preview = next(arg.removeprefix("--preview=") for arg in capture["args"] if arg.startswith("--preview="))
        preview = preview.replace("{2}", shlex.quote(parent)).replace("{3}", "3")
        self.assertIn("redis", self.check_ok(self.run_command(["/bin/sh", "-c", preview])))

    def test_demo_fails_closed_without_isolated_wrapper(self):
        tape = (ROOT / "docs/demo.tape").read_text()
        self.assertIn('Require "/tmp/pisearch-demo-bin/pi-search"', tape)
        self.assertIn('Type "/tmp/pisearch-demo-bin/pi-search -d redis"', tape)
        self.assertNotIn('Type "pi-search ', tape)


if __name__ == "__main__":
    unittest.main()
