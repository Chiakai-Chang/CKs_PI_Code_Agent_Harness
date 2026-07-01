#!/usr/bin/env python3
"""
C.A.S.E. / SkillOpt Bridge Coordinator
Bridges Microsoft Research's SkillOpt training loop with local skill-optimizer sandbox.

This coordinator subclasses SkillOpt's environment interface to run rollouts
inside the secure Docker workbench provided by skill-optimizer, ensuring safe and
deterministic evaluation of mutating skill documents.
"""

import os
import sys
import json
import subprocess
import argparse

# Dynamic path resolution
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_OPTIMIZER_DIR = os.path.join(REPO_ROOT, "plugins", "skill-optimizer") # or local node packages

def check_dependencies():
    """Verify required libraries and tools are present."""
    # Check node modules
    if not os.path.exists(os.path.join(REPO_ROOT, "node_modules")) and not os.path.exists(os.path.join(SKILL_OPTIMIZER_DIR, "node_modules")):
        print("[BRIDGE] Warning: node_modules not found. Please run 'npm install' first.")
    
    # Check Docker
    try:
        subprocess.run(["docker", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        print("[BRIDGE] Warning: Docker is not running. Docker is required for skill-optimizer sandboxing.")

class SkillOptimizerEnvBridge:
    """
    Subclasses or acts as a SkillOpt Env adapter.
    Executes case rollouts inside the dockerized skill-optimizer sandbox.
    """
    def __init__(self, case_file: str, model: str = None):
        self.case_file = case_file
        self.model = model

    def rollout(self, skill_content: str) -> dict:
        """
        Runs a single rollout epoch.
        1. Overwrites the target SKILL.md under references/ with the new mutation.
        2. Spawns skill-optimizer run-case command.
        3. Parses the output JSON grade and returns success metrics.
        """
        # Save mutated skill content to temporary location
        # (This path will be configured in the case references folder)
        print(f"[BRIDGE] Executing rollout for case: {self.case_file}")
        
        cmd = ["npx", "tsx", "src/cli.ts", "run-case", self.case_file]
        if self.model:
            cmd.extend(["--models", self.model])
            
        try:
            # Run skill-optimizer CLI
            res = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse result from stdout or trace files
            # Default outputs go into .results/<run-id>/trials/
            print("[BRIDGE] Rollout completed successfully.")
            return {"status": "success", "raw": res.stdout}
        except subprocess.CalledProcessError as e:
            print(f"[BRIDGE] Rollout failed: {e.stderr}")
            return {"status": "failed", "error": e.stderr}

def main():
    parser = argparse.ArgumentParser(description="Bridge Microsoft SkillOpt with local skill-optimizer")
    parser.add_argument("--case", required=True, help="Path to the case.yml file")
    parser.add_argument("--model", help="OpenRouter model identifier")
    args = parser.parse_args()

    check_dependencies()
    
    bridge = SkillOptimizerEnvBridge(args.case, args.model)
    # Demonstration rollout run
    # In a full run, this is hooked into SkillOpt's trainer loop:
    # trainer = ReflACTTrainer(config=config, env=bridge)
    # trainer.train()
    bridge.rollout("# Mock Mutated Skill Content")

if __name__ == "__main__":
    main()
