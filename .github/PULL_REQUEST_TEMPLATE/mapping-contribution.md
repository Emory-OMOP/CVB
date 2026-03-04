## Mapping Contribution

**Vocabulary**: <!-- e.g., PSYCHIATRY, CARDIOLOGY -->
**Contributor**: <!-- Your name / organization -->

### Summary

<!-- Brief description of the mappings being added or updated -->

### Checklist

- [ ] CSV is UTF-8 encoded with standard headers
- [ ] All required columns present: `source_concept_code`, `source_vocabulary_id`, `source_description`, `predicate_id`, `confidence`, `target_concept_id`
- [ ] `predicate_id` uses valid predicates (`exactMatch`, `broadMatch`, `narrowMatch`, `noMatch` — or OHDSI codes `eq`, `up`, `down`; `skos:` prefixed forms accepted)
- [ ] `confidence` values are between 0 and 1
- [ ] No duplicate `source_concept_code` values within the file
- [ ] `target_concept_id` references valid OMOP concept IDs (or 0 for `skos:noMatch`)
- [ ] `source_vocabulary_id` matches the target vocabulary

### Mapping Statistics

| Metric | Count |
|--------|-------|
| Total rows | |
| exactMatch (eq) | |
| broadMatch (up) | |
| narrowMatch (down) | |
| noMatch (new concepts) | |

### Review Notes

<!-- Any context for reviewers: clinical domain, source data, methodology -->
