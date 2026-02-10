import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
import sys
import os

# Add src to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestFileOrganizerCLI(unittest.TestCase):
    """Tests for the file organizer CLI following TDD approach."""

    def setUp(self):
        """Copy visible sample test files to temp dir for testing."""
        self.test_dir = Path(tempfile.mkdtemp())
        # Visible samples to run tests on (copied here)
        self.sample_files = ["document.txt", "image.jpg", "script.py", "video.mp4", "unknown.xyz", "audio.mp3"]
        samples_dir = Path(__file__).parent.parent / "samples"
        for fname in self.sample_files:
            shutil.copy(samples_dir / fname, self.test_dir / fname)
        # Subdir to test ignore logic
        (self.test_dir / "ignore_me").mkdir()

    def tearDown(self):
        """Revert/clean up test directory to original empty state."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def run_cli(self, args):
        """Run the CLI via subprocess for integration test."""
        cmd = [sys.executable, '-m', 'file_organizer.cli', str(self.test_dir)] + args
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent.parent / 'src')
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
        return result

    def test_organize_files(self):
        """Test full organization functionality."""
        # Run without dry-run
        result = self.run_cli([])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Organization complete!", result.stdout)
        self.assertIn("Metrics (mode:", result.stdout)  # New summary with mode

        # Verify categories and moves (reverted state checked in tearDown)
        # Note: folders/ now included for ignore_me dir in type mode
        expected_categories = {"documents", "images", "code", "videos", "audio", "other", "folders"}
        for cat in expected_categories:
            cat_dir = self.test_dir / cat
            self.assertTrue(cat_dir.exists() and cat_dir.is_dir())

        # Check counts (1 each + folders)
        self.assertEqual(len(list((self.test_dir / "documents").iterdir())), 1)
        self.assertEqual(len(list((self.test_dir / "images").iterdir())), 1)
        self.assertEqual(len(list((self.test_dir / "code").iterdir())), 1)
        self.assertEqual(len(list((self.test_dir / "videos").iterdir())), 1)
        self.assertEqual(len(list((self.test_dir / "audio").iterdir())), 1)
        self.assertEqual(len(list((self.test_dir / "other").iterdir())), 1)
        self.assertEqual(len(list((self.test_dir / "folders").iterdir())), 1)  # ignore_me

        # Original files should be gone from root
        for fname in self.sample_files:
            self.assertFalse((self.test_dir / fname).exists())

    def test_dry_run(self):
        """Test dry-run mode doesn't modify files."""
        # Run dry-run
        result = self.run_cli(['--dry-run'])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Dry run completed.", result.stdout)
        self.assertIn("Would move: document.txt -> documents/document.txt", result.stdout)  # Relative

        # Verify no changes (all files still in root)
        for fname in self.sample_files:
            self.assertTrue((self.test_dir / fname).exists())
        # No category dirs created
        self.assertFalse((self.test_dir / "documents").exists())


if __name__ == '__main__':
    unittest.main()
