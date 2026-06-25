"""Detect exact and quality-variant media files.

Three group types
  exact    — identical bytes (size + partial_hash + full_hash)
  quality  — same TMDB entity + same episode code + different file path / resolution
  possible — same show title AND same episode code, clearly different quality/folder

Key guards
  0. Same-path guard     : same file_path → same physical file, never a duplicate
  1. Show-title guard    : show titles must score ≥ 0.80 before episode-code pairing
                           — prevents Dexter S01E01 vs Die.Hart S01E01
  2. Episode-code guard  : only pair files that share the same SxxExx code
  3. Same-folder guard   : files in the same folder are different episodes of same show
  4. Size guard          : > 500 MB difference → very unlikely to be same content
  Duration is deliberately NOT used — TV episodes share runtimes too easily.
"""
import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher

from mlm.db.connection import get_connection
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5
from mlm.utils.similarity import text_similarity
# NOTE: `same_episode` removed from this import — it was unused (issue #7).
# The module uses its own _EP_CODE_RE / ep_code_re inline regex instead.

log = logging.getLogger(__name__)

_MAX_SIZE_DIFF_BYTES  = 500 * 1024 * 1024   # 500 MB
_MIN_NAME_SCORE       = 0.70                 # normalised full-name similarity
_MIN_TITLE_SIMILARITY = 0.80                 # show-title-only gate

_EP_CODE_RE = re.compile(r'[Ss]\d{1,2}[Ee]\d{1,2}.*', re.IGNORECASE)
_STRIP_RE   = re.compile(
    r'\b('
    r'bluray|blu-ray|bdrip|brrip|webrip|web-dl|web|hdtv|dvdrip|dvd|'
    r'1080p|720p|480p|2160p|4k|uhd|hdr|'
    r'x264|x265|h264|h265|hevc|avc|xvid|divx|'
    r'aac|ac3|dts|ddp|atmos|truehd|flac|mp3|'
    r'remux|repack|proper|extended|theatrical|'
    r'yts|rarbg|ettv|ion10|glhf|smurf|kontrast|ntg|bia|cm|'
    r'\d{4}'  # year
    r')\b',
    re.IGNORECASE,
)
_QUALITY_TAGS = re.compile(
    r'\b(1080p|720p|480p|2160p|4k|uhd|bluray|blu-ray|webrip|web-dl|hdtv|bdrip)\b',
    re.IGNORECASE,
)
_PUNC_RE = re.compile(r'[._\-\[\](){}]+')


def _extract_show_title(filename: str) -> str:
    name = re.sub(r'\.[a-zA-Z0-9]{2,5}$', '', filename)
    name = _EP_CODE_RE.sub('', name)
    name = _PUNC_RE.sub(' ', name)
    name = _STRIP_RE.sub(' ', name)
    return re.sub(r'\s{2,}', ' ', name).strip().lower()


def _title_similar(a: str, b: str) -> bool:
    ta = _extract_show_title(a)
    tb = _extract_show_title(b)
    if not ta or not tb:
        return True
    return SequenceMatcher(None, ta, tb).ratio() >= _MIN_TITLE_SIMILARITY


def _quality_tags_set(name: str) -> set[str]:
    return {m.group(0).lower() for m in _QUALITY_TAGS.finditer(name)}


def _normalise(name: str) -> str:
    name = name.rsplit('.', 1)[0]
    name = name.replace('.', ' ').replace('_', ' ')
    name = _STRIP_RE.sub('', name)
    return re.sub(r'\s{2,}', ' ', name).strip().lower()


class DuplicateService:
    def __init__(
        self,
        repo: DuplicatesRepository | None = None,
        files_repo: FilesRepository | None = None,
    ) -> None:
        self.repo       = repo or DuplicatesRepository()
        self.files_repo = files_repo or FilesRepository()

    def _list_candidate_files(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, entity_id, file_name, file_path, file_size_bytes,
                       duration_seconds, partial_hash, full_hash,
                       resolution, video_codec, parent_folder
                FROM media_files
                WHERE removed_at IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def build_duplicate_groups(self) -> dict:
        files = self._list_candidate_files()
        self.repo.clear_non_ignored_groups()
        ignored_ids: set[int] = self._ignored_file_ids()

        log.info("Building duplicate groups from %d candidate files", len(files))

        used_ids: set[int] = set()
        exact_groups   = self._build_exact_duplicates(files, used_ids)
        quality_groups = self._build_quality_variants(files, used_ids)
        remaining      = [f for f in files if f['id'] not in used_ids]
        possible_groups = self._build_possible_duplicates(remaining, ignored_ids)

        log.info(
            "Scan complete: %d exact, %d quality-variant, %d possible",
            exact_groups, quality_groups, possible_groups,
        )
        return {
            'exact_groups':    exact_groups,
            'quality_groups':  quality_groups,
            'possible_groups': possible_groups,
        }

    def _build_exact_duplicates(self, files: list[dict], used_ids: set[int]) -> int:
        by_size: dict[int, list[dict]] = defaultdict(list)
        for row in files:
            by_size[row['file_size_bytes']].append(row)

        group_count = 0
        for items in by_size.values():
            if len(items) < 2:
                continue
            by_partial: dict[str, list[dict]] = defaultdict(list)
            for item in items:
                try:
                    by_partial[self._compute_partial(item)].append(item)
                except OSError as exc:
                    log.warning("Cannot hash %s: %s", item['file_path'], exc)

            for partial_items in by_partial.values():
                if len(partial_items) < 2:
                    continue
                by_full: dict[str, list[dict]] = defaultdict(list)
                for item in partial_items:
                    try:
                        by_full[self._compute_full(item)].append(item)
                    except OSError as exc:
                        log.warning("Cannot full-hash %s: %s", item['file_path'], exc)

                for full_items in by_full.values():
                    if len(full_items) < 2:
                        continue
                    gid = self.repo.create_group('exact', 1.0)
                    for item in full_items:
                        self.repo.add_item(gid, item['id'], 1.0, {'reason': 'identical'})
                        used_ids.add(item['id'])
                    group_count += 1

        return group_count

    def _build_quality_variants(self, files: list[dict], used_ids: set[int]) -> int:
        entity_buckets: dict[int, list[dict]] = defaultdict(list)
        for f in files:
            if f['entity_id'] is not None:
                entity_buckets[f['entity_id']].append(f)

        file_ids = [f['id'] for f in files if f['entity_id'] is not None]
        ep_map: dict[int, tuple[int, int]] = {}
        if file_ids:
            placeholders = ','.join('?' * len(file_ids))
            with get_connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT media_file_id, season_number, episode_number
                    FROM episodes
                    WHERE media_file_id IN ({placeholders}) AND is_missing = 0
                    """,
                    file_ids,
                ).fetchall()
            for r in rows:
                ep_map[r['media_file_id']] = (r['season_number'], r['episode_number'])

        group_count = 0
        for entity_id, members in entity_buckets.items():
            if len(members) < 2:
                continue
            sub_buckets: dict[tuple, list[dict]] = defaultdict(list)
            for f in members:
                key = ep_map.get(f['id'], (0, 0))
                sub_buckets[key].append(f)

            for sub_members in sub_buckets.values():
                if len(sub_members) < 2:
                    continue
                if len({f['file_path'] for f in sub_members}) < 2:
                    continue
                resolutions = {f.get('resolution') for f in sub_members if f.get('resolution')}
                codecs      = {f.get('video_codec') for f in sub_members if f.get('video_codec')}
                if len(resolutions) < 2 and len(codecs) < 2:
                    continue
                gid = self.repo.create_group('quality', 1.0)
                for item in sub_members:
                    self.repo.add_item(gid, item['id'], 1.0, {
                        'reason':     'same_entity_diff_quality',
                        'resolution': item.get('resolution'),
                        'codec':      item.get('video_codec'),
                    })
                    used_ids.add(item['id'])
                group_count += 1

        return group_count

    def _build_possible_duplicates(
        self, files: list[dict], ignored_ids: set[int]
    ) -> int:
        group_count = 0
        used_pairs: set[tuple[int, int]] = set()

        ep_code_re = re.compile(r'[Ss](\d{1,2})[Ee](\d{1,2})')

        ep_title_buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
        no_code: list[dict] = []

        for f in files:
            if f['id'] in ignored_ids:
                continue
            m = ep_code_re.search(f['file_name'])
            if m:
                show_title = _extract_show_title(f['file_name'])
                ep_key     = m.group(0).upper()
                ep_title_buckets[(show_title, ep_key)].append(f)
            else:
                no_code.append(f)

        def _check_pair(a: dict, b: dict) -> None:
            nonlocal group_count

            if a['file_path'] and b['file_path'] and a['file_path'] == b['file_path']:
                return

            pair_key = (min(a['id'], b['id']), max(a['id'], b['id']))
            if pair_key in used_pairs:
                return

            if (a.get('parent_folder') and b.get('parent_folder') and
                    a['parent_folder'] == b['parent_folder']):
                return

            if abs(a['file_size_bytes'] - b['file_size_bytes']) > _MAX_SIZE_DIFF_BYTES:
                return

            name_score   = text_similarity(_normalise(a['file_name']), _normalise(b['file_name']))
            if name_score < _MIN_NAME_SCORE:
                return

            tags_a       = _quality_tags_set(a['file_name'])
            tags_b       = _quality_tags_set(b['file_name'])
            quality_diff = 1.0 if tags_a != tags_b else 0.0
            score        = round((name_score * 0.70) + (quality_diff * 0.30), 3)

            if score < _MIN_NAME_SCORE:
                return

            used_pairs.add(pair_key)
            gid = self.repo.create_group('possible', score)
            for item in (a, b):
                self.repo.add_item(gid, item['id'], score, {
                    'name_score':   name_score,
                    'quality_diff': quality_diff,
                    'tags_a':       list(tags_a),
                    'tags_b':       list(tags_b),
                })
            group_count += 1

        for bucket_files in ep_title_buckets.values():
            for i, a in enumerate(bucket_files):
                for b in bucket_files[i + 1:]:
                    _check_pair(a, b)

        for i, a in enumerate(no_code):
            for b in no_code[i + 1:]:
                if not _title_similar(a['file_name'], b['file_name']):
                    continue
                _check_pair(a, b)

        return group_count

    def _ignored_file_ids(self) -> set[int]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT di.media_file_id
                FROM duplicate_items di
                JOIN duplicate_groups dg ON dg.id = di.group_id
                WHERE dg.review_status = 'ignored'
                """
            ).fetchall()
        return {r[0] for r in rows}

    def _compute_partial(self, item: dict) -> str:
        if item['partial_hash']:
            return item['partial_hash']
        h = partial_md5(item['file_path'])
        self.files_repo.save_hashes(file_path=item['file_path'], partial_hash=h)
        item['partial_hash'] = h
        return h

    def _compute_full(self, item: dict) -> str:
        if item['full_hash']:
            return item['full_hash']
        h = full_md5(item['file_path'])
        self.files_repo.save_hashes(file_path=item['file_path'], full_hash=h)
        item['full_hash'] = h
        return h
