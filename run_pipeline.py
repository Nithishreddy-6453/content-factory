import os
import sys
import argparse
from core.db import Database as DBManager
from agents.manager_agent import ManagerAgent

def main():
    parser = argparse.ArgumentParser(description="Standalone Production Entry Point")
    parser.add_argument("niche", help="The niche to run")
    parser.add_argument("--run-id", help="Resume an existing run_id", default=None)
    args = parser.parse_args()
    
    print(f"Starting standalone pipeline for niche: {args.niche}")
    if args.run_id:
        print(f"Resuming run: {args.run_id}")
        
    manager = ManagerAgent(args.niche)
    manager.execute_workflow(run_id=args.run_id)

if __name__ == "__main__":
    main()
