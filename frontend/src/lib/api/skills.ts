/**
 * Skills API
 *
 * Functions for managing skills.
 */

import { api } from './client';
import { SkillInfo } from './types';

/**
 * Get all skills
 */
export async function getSkills(): Promise<SkillInfo[]> {
  return api.get<SkillInfo[]>('/v1/api/skills');
}

/**
 * Get a specific skill by ID
 */
export async function getSkill(skillId: number): Promise<SkillInfo> {
  return api.get<SkillInfo>(`/v1/api/skills/${skillId}`);
}
