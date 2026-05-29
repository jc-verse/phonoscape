# PyView

Python port of MView

```bash
uv sync
source .venv/bin/activate
```

```bash
python -m pyview ./S02_data.mat --palate S02_pal --spline td tb tt
```

```bash
uv run datamodel-codegen \
  --input ../schemas/protocol.json \
  --input-file-type jsonschema \
  --output src/pyviewbe/protocol.py \
  --output-model-type pydantic_v2.BaseModel
```
