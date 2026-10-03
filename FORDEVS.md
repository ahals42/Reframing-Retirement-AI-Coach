# Developer reference: data across versions

## Data per version

| Version | Master file | Lessons | Science modules | Collections (master / activities / home) | Local port |
|---|---|---|---|---|---|
| 1-10 | `New-RR-Master-File.txt` | 1-10 | 1-3, 4-6, 7-10 | `rr_master` / `rr_activities` / `rr_home` | 8000 |
| 1-6 | `lesson-6-master-file.txt` | 1-6 | 1-3, 4-6 | `rr_master_l6` / `rr_activities_l6` / `rr_home_l6` | 8001 |
| 1-3 | `lesson-3-master-file.txt` | 1-3 | 1-3 | `rr_master_l3` / `rr_activities_l3` / `rr_home_l3` | 8002 |

The activity list and at-home resource list are the same files in every version. Each version still has its own collections.

## Files

- `data/`: master lesson file for the version, activity list, at-home resource list.
- `rag/config.py`: default data paths and collection names.
- `rag/ingest.py`: builds the Qdrant collections from the data files.
- `.env.example`: environment variables, including the collection names.

## Ingest data for this version

```
docker compose up -d qdrant
python -m rag.ingest
```

## Verify

Open the Qdrant dashboard at http://localhost:6333/dashboard. It lists every collection from every version.

To check one collection from the command line:

```
curl -s localhost:6333/collections/rr_master
```

The `points_count` should match the number of slides in the master file for that version (see the counts below).

Expected master point counts: 1-10 = 412, 1-6 = 240, 1-3 = 131.

## Change one version's data

1. Edit or replace that version's master file in `data/`, or point `RR_MASTER_DATA_PATH` at a different file.
2. Keep the collection names in `.env` unique to that version.
3. Re-run ingest. It deletes and rebuilds only the collections named in that version's `.env`.
4. Check the collection with the commands above.

Never point two versions at the same collection names. Ingest deletes and recreates them.

## How the version files were cut

The lesson files are line ranges of `New-RR-Master-File.txt`:

- Lessons 1-3 version: lines 1-1358 (Lessons 1-3 and Science 1-3).
- Lessons 1-6 version: lines 1-2510 (Lessons 1-6 and Science 1-3 and 4-6).

The lesson 4 block starts at line 1359 and the lesson 7 block at line 2511 in the full file.

## Scope text that depends on the data

If a version's lessons change, the matching text also needs updating:

- `coach/prompts.py`: topic-to-lesson map and the LATER CONTENT block.
- `coach/weekly_focus.py`: lesson goals, week tables and the out-of-range message.
