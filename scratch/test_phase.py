import asyncio
import os
from workflow.phases import PhaseRunner
from workflow.artifact_store import ArtifactStore
from workflow.models import ModelRoutingConfig

async def test_phase():
    store = ArtifactStore(artifacts_root=".data/workflow/artifacts", db_path=".data/workflow/workflow.db")
    runner = PhaseRunner(
        ollama_base="http://localhost:11434",
        artifact_store=store
    )
    
    run_id = "test_run_1"
    request = "Create a CPU monitor script."
    routing = ModelRoutingConfig()
    
    print(f"Running context phase for {run_id}...")
    try:
        art = await runner.run_phase(
            run_id=run_id,
            phase="context",
            request=request,
            routing=routing,
            prior_artifacts=[]
        )
        print(f"Success! Artifact: {art.name}")
        print(f"Content length: {len(store.get_content(art.artifact_id))}")
    except Exception as e:
        print(f"Phase failed with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_phase())
