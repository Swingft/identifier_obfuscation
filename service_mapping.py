#!/usr/bin/env python3
"""
Service Mapping Script
간단한 서비스용 매핑 스크립트

사용법:
  python3 service_mapping.py --targets targets.json --output mapping_result.json

입력:
  - targets.json: 매핑할 타겟 리스트 (여러 포맷 지원)
  - name_clusters/ 폴더: 사전 준비된 군집화 결과 (cluster_index_<kind>.json, safe_pool_<kind>.txt)

출력:
  - mapping_result.json: 매핑 결과
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

# Shared identifier utilities
from utils.identifier_utils import (
    split_ident,
    detect_casing_for_mapping,
    normalize,
    jaro_winkler,
    STOP_TOKENS,
    tokens_no_stop,
)

# 기본 설정값들
DEFAULT_JW_THRESHOLD = 0.88
DEFAULT_AVOID_PREFIX = 3
DEFAULT_KEEP_CASE = True
DEFAULT_SEED = 42
DEFAULT_FC_K = 600
DEFAULT_FC_TOKEN_OVERLAP = 0
DEFAULT_FC_LEN_DIFF = 2
DEFAULT_FC_PREFIX = 3

SUPPORTED_KINDS = ["class", "struct", "enum", "protocol", "extension", "typealias", "function", "variable"]


def load_targets_from_json(targets_path: Path) -> Dict[str, List[str]]:
    """다양한 포맷의 targets.json을 로드하여 종류별로 분류"""
    data = json.loads(targets_path.read_text(encoding='utf-8'))
    
    # 포맷 1: {"class": ["A","B"], "function": ["C","D"]}
    if isinstance(data, dict):
        result = {}
        for kind in SUPPORTED_KINDS:
            if kind in data and isinstance(data[kind], list):
                result[kind] = [str(x) for x in data[kind]]
        if result:
            return result
        
        # 포맷 2: {"kind": "class", "names": ["A","B"]}
        kind = data.get('kind') or data.get('type')
        if isinstance(kind, str) and kind.lower() in SUPPORTED_KINDS:
            arr = data.get('names') or data.get('list')
            if isinstance(arr, list):
                return {kind.lower(): [str(x) for x in arr]}
        
        # 포맷 3: {"names": ["A","B"]} - 기본적으로 function으로 분류
        arr = data.get('names') or data.get('list')
        if isinstance(arr, list):
            return {"function": [str(x) for x in arr]}
    
    # 포맷 4: ["A","B"] - 기본적으로 function으로 분류
    if isinstance(data, list):
        return {"function": [str(x) for x in data]}
    
    raise ValueError(f"지원되지 않는 targets.json 포맷입니다: {targets_path}")


def load_candidates(pool_dir: Path, kind: str) -> List[str]:
    """후보 풀 로드"""
    safe = pool_dir / f"safe_pool_{kind}.txt"
    buckets = pool_dir / f"buckets_pool_{kind}.txt"
    path = safe if safe.exists() else buckets
    
    if not path.exists():
        raise FileNotFoundError(f"후보 풀 파일을 찾을 수 없습니다: {path}")
    
    names = [l.strip() for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
    return names


def load_cluster_index(index_dir: Path, kind: str) -> List[Dict[str, Any]]:
    """클러스터 인덱스 로드"""
    path = index_dir / f"cluster_index_{kind}.json"
    if not path.exists():
        raise FileNotFoundError(f"클러스터 인덱스 파일을 찾을 수 없습니다: {path}")
    
    data = json.loads(path.read_text(encoding='utf-8'))
    return data


def cluster_distance_for_target(target: str, cl: dict) -> float:
    """타겟과 클러스터 대표값 간의 거리 계산"""
    tnorm = normalize(target)
    rnorm = normalize(cl['rep']) if cl['rep'] else ''
    
    # Jaro-Winkler 거리
    jw_rep = jaro_winkler(tnorm, rnorm) if rnorm else 0.0
    
    # 토큰 Jaccard 거리
    tset = {t.lower() for t in tokens_no_stop(target)}
    cset = {t.lower() for t in cl.get('tokens', []) if t and t.lower() not in STOP_TOKENS}
    jac = (len(tset & cset) / max(1, len(tset | cset))) if (tset or cset) else 0.0
    
    # 길이 차이
    len_gap = min(abs(len(tnorm) - len(rnorm)), 8) / 8.0 if rnorm else 1.0
    
    # 접두어/접미어 중복
    prefix_hit = 1.0 if (rnorm[:3] and rnorm[:3] == tnorm[:3]) else 0.0
    suffix_hit = 1.0 if (rnorm[-2:] and rnorm[-2:] == tnorm[-2:]) else 0.0
    
    # 가중치 합산
    w1, w2, w3, w4, w5 = 0.50, 0.25, 0.15, 0.05, 0.05
    distance = w1*(1.0 - jw_rep) + w2*(1.0 - jac) + w3*(len_gap) + w4*(prefix_hit) + w5*(suffix_hit)
    
    return distance


def select_far_clusters(index_dir: Path, kind: str, target: str, k: int, 
                       token_overlap: int, min_len_diff: int, prefix_guard: int) -> List[Dict[str, Any]]:
    """타겟과 먼 클러스터들 선택"""
    clusters = load_cluster_index(index_dir, kind)
    tnorm = normalize(target)
    tset = {t.lower() for t in tokens_no_stop(target)}
    
    # 필터링
    blocked = []
    for cl in clusters:
        rep = cl['rep'] or ''
        rnorm = normalize(rep) if rep else ''
        cset = {t.lower() for t in cl.get('tokens', []) if t and t.lower() not in STOP_TOKENS}
        
        if len(tset & cset) > token_overlap:
            continue
        if rnorm and abs(len(tnorm) - len(rnorm)) < min_len_diff:
            continue
        if prefix_guard > 0 and rnorm and tnorm[:prefix_guard] == rnorm[:prefix_guard]:
            continue
        
        blocked.append(cl)
    
    # 거리 순 정렬
    scored = [(cluster_distance_for_target(target, cl), cl) for cl in blocked]
    scored.sort(key=lambda x: x[0], reverse=True)
    
    return [cl for _, cl in scored[:k]]


def create_mapping(targets: List[str], pool_dir: Path, index_dir: Path, kind: str, 
                  rnd: random.Random) -> List[Dict[str, str]]:
    """매핑 생성"""
    # 후보 풀 로드
    candidates = load_candidates(pool_dir, kind)
    targets_set = set(targets)
    candidates = [n for n in candidates if n not in targets_set]
    
    # 매핑 생성
    mapping = []
    avail = set(candidates)
    
    for target in targets:
        # 원거리 클러스터 선택
        far_clusters = select_far_clusters(
            index_dir, kind, target,
            DEFAULT_FC_K, DEFAULT_FC_TOKEN_OVERLAP,
            DEFAULT_FC_LEN_DIFF, DEFAULT_FC_PREFIX
        )
        
        # 클러스터 멤버만 후보로 제한
        member_set = set()
        for cl in far_clusters:
            for m in cl.get('members', []):
                member_set.add(m)
        
        per_target_pool = [n for n in avail if n in member_set]
        if not per_target_pool:
            per_target_pool = list(avail)  # 폴백
        
        # 케이스 필터링
        if DEFAULT_KEEP_CASE:
            tcase = detect_casing_for_mapping(target)
            per_target_pool = [n for n in per_target_pool if detect_casing_for_mapping(n) == tcase]
        
        # 접두어 가드
        if DEFAULT_AVOID_PREFIX > 0:
            per_target_pool = [n for n in per_target_pool 
                             if not (target[:DEFAULT_AVOID_PREFIX] and 
                                   n[:DEFAULT_AVOID_PREFIX] == target[:DEFAULT_AVOID_PREFIX])]
        
        # 유사도 필터링
        tnorm = normalize(target)
        per_target_pool = [n for n in per_target_pool 
                          if jaro_winkler(normalize(n), tnorm) <= DEFAULT_JW_THRESHOLD]
        
        # 선택
        if per_target_pool:
            chosen = rnd.choice(per_target_pool)
            avail.remove(chosen)
            mapping.append({"target": target, "replacement": chosen})
        else:
            # 실패 시 조건 완화
            for jw_cap in [DEFAULT_JW_THRESHOLD + 0.02, DEFAULT_JW_THRESHOLD + 0.04, 
                          DEFAULT_JW_THRESHOLD + 0.06, DEFAULT_JW_THRESHOLD + 0.08]:
                relaxed_pool = [n for n in avail 
                              if jaro_winkler(normalize(n), tnorm) <= jw_cap]
                if relaxed_pool:
                    chosen = rnd.choice(relaxed_pool)
                    avail.remove(chosen)
                    mapping.append({"target": target, "replacement": chosen})
                    break
    
    return mapping


def main():
    parser = argparse.ArgumentParser(description="서비스용 매핑 스크립트")
    parser.add_argument("--targets", required=True, help="타겟 리스트 JSON 파일")
    parser.add_argument("--output", required=True, help="출력 JSON 파일")
    parser.add_argument("--pool-dir", default="name_clusters", help="후보 풀 디렉터리 (기본: name_clusters)")
    parser.add_argument("--index-dir", default="name_clusters", help="클러스터 인덱스 디렉터리 (기본: name_clusters)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="랜덤 시드")
    
    args = parser.parse_args()
    
    # 입력 검증
    targets_path = Path(args.targets)
    if not targets_path.exists():
        print(f"타겟 파일을 찾을 수 없습니다: {targets_path}", file=sys.stderr)
        sys.exit(1)
    
    pool_dir = Path(args.pool_dir)
    index_dir = Path(args.index_dir)
    
    if not pool_dir.exists():
        print(f"후보 풀 디렉터리를 찾을 수 없습니다: {pool_dir}", file=sys.stderr)
        sys.exit(1)
    
    if not index_dir.exists():
        print(f"클러스터 인덱스 디렉터리를 찾을 수 없습니다: {index_dir}", file=sys.stderr)
        sys.exit(1)
    
    # 타겟 로드
    try:
        targets_by_kind = load_targets_from_json(targets_path)
    except Exception as e:
        print(f"타겟 파일 로드 실패: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not targets_by_kind:
        print("유효한 타겟을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    
    # 매핑 생성
    rnd = random.Random(args.seed)
    result = {}
    
    for kind, targets in targets_by_kind.items():
        try:
            mapping = create_mapping(targets, pool_dir, index_dir, kind, rnd)
            result[kind] = mapping
            print(f"[{kind}] {len(mapping)}/{len(targets)} 매핑 생성")
        except Exception as e:
            print(f"[{kind}] 매핑 실패: {e}", file=sys.stderr)
            result[kind] = []
    
    # 결과 저장
    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"매핑 결과 저장: {output_path}")


if __name__ == "__main__":
    main()
