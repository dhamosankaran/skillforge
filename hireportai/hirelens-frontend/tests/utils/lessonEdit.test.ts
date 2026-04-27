import { describe, it, expect } from 'vitest'
import {
  classifyEdit,
  classifyLessonEdit,
  SUBSTANTIVE_EDIT_THRESHOLD,
} from '@/utils/lessonEdit'

describe('classifyEdit (Phase 6 slice 6.4b — D-17 advisory)', () => {
  it('returns minor on a 1-char typo fix', () => {
    expect(classifyEdit('Hello world', 'Hello world!')).toBe('minor')
  })

  it('returns substantive on a full-string replacement', () => {
    expect(classifyEdit('a'.repeat(100), 'b'.repeat(100))).toBe('substantive')
  })

  it('treats threshold as strict greater-than (>0.15 → substantive)', () => {
    expect(SUBSTANTIVE_EDIT_THRESHOLD).toBe(0.15)
    // 100-char before; 15 char-substitutions → ratio 0.15 exactly → minor.
    const before = 'a'.repeat(100)
    const after = 'b'.repeat(15) + 'a'.repeat(85)
    expect(classifyEdit(before, after)).toBe('minor')

    // 16 substitutions → ratio 0.16 → substantive.
    const after2 = 'b'.repeat(16) + 'a'.repeat(84)
    expect(classifyEdit(before, after2)).toBe('substantive')
  })
})

describe('classifyLessonEdit (max-of-three semantic per spec §7.1)', () => {
  it('returns substantive when ANY field exceeds the threshold', () => {
    const before = {
      concept_md: 'a'.repeat(100),
      production_md: 'a'.repeat(100),
      examples_md: 'a'.repeat(100),
    }
    const after = {
      concept_md: 'a'.repeat(100), // unchanged
      production_md: 'a'.repeat(100), // unchanged
      examples_md: 'b'.repeat(100), // fully replaced — exceeds threshold
    }
    expect(classifyLessonEdit(before, after)).toBe('substantive')
  })

  it('returns minor when all three field deltas are under threshold', () => {
    const before = {
      concept_md: 'concept original text',
      production_md: 'production original text',
      examples_md: 'examples original text',
    }
    const after = {
      concept_md: 'concept original text.', // 1-char addition
      production_md: 'production original text',
      examples_md: 'examples original text',
    }
    expect(classifyLessonEdit(before, after)).toBe('minor')
  })
})
