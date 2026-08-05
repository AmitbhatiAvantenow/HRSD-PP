import json
import re
import csv
import io
import random
import logging
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

from odoo import http
from odoo.http import request

from .controllers import get_hrsd_branding, require_hrsd_confidential_access

_logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE INTERVIEW QUESTION BANK
# ═══════════════════════════════════════════════════════════════════════════════

BEHAVIORAL_QUESTIONS = {
    'leadership': [
        {
            'text': "Tell me about a time when you had to lead a team through a difficult situation. What was your approach and what was the outcome?",
            'follow_ups': ["How did you handle team members who were resistant to your direction?", "What would you do differently if faced with the same situation today?"],
            'tips': "Look for evidence of clear direction-setting, team motivation, and results orientation.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where you had to influence people who did not directly report to you. How did you gain their support?",
            'follow_ups': ["What obstacles did you encounter?", "How did you measure the success of your influence?"],
            'tips': "Assess stakeholder management, persuasion skills, and political savvy.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of when you had to make a tough decision that not everyone on your team agreed with. How did you handle the pushback?",
            'follow_ups': ["How did the outcome affect team morale?", "How would you improve your communication approach?"],
            'tips': "Look for decisiveness, courage, and the ability to bring people along after a decision.",
            'levels': ['senior', 'executive'],
        },
        {
            'text': "Tell me about a time you mentored or coached a team member who was underperforming. What steps did you take?",
            'follow_ups': ["What was the result after your coaching?", "What did you learn about your own leadership style from this experience?"],
            'tips': "Assess coaching skills, patience, and ability to develop others.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where you had to lead a cross-functional initiative. How did you align everyone toward a common goal?",
            'follow_ups': ["What was the biggest challenge in managing across functions?", "How did you handle conflicting priorities from different teams?"],
            'tips': "Look for collaboration skills, alignment techniques, and executive communication.",
            'levels': ['senior', 'executive'],
        },
        {
            'text': "Tell me about a time you had to manage up — when you needed to convince your manager or senior leadership to change direction.",
            'follow_ups': ["How did you prepare your case?", "What happened and what did you learn?"],
            'tips': "Assess courage, data-driven thinking, and the ability to challenge authority respectfully.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time you successfully delegated a high-stakes task. How did you decide what to delegate and to whom?",
            'follow_ups': ["How did you ensure accountability without micromanaging?", "What would you do differently?"],
            'tips': "Look for trust in others, effective delegation, and a non-micromanaging leadership style.",
            'levels': ['mid', 'senior', 'executive'],
        },
    ],
    'communication': [
        {
            'text': "Tell me about a time when you had to communicate a complex technical concept to a non-technical audience. How did you approach it?",
            'follow_ups': ["How did you confirm they understood?", "What feedback did you receive?"],
            'tips': "Look for clarity, audience awareness, and the use of analogies or visuals.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where miscommunication caused a problem. What happened, and what did you learn from it?",
            'follow_ups': ["What steps did you take to resolve the miscommunication?", "How did you prevent similar issues in the future?"],
            'tips': "Look for self-awareness, accountability, and lessons learned.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of a time you had to deliver difficult feedback. How did you prepare and deliver it?",
            'follow_ups': ["How did the person respond?", "What was the outcome?"],
            'tips': "Assess empathy, directness, and ability to deliver constructive criticism effectively.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time you successfully persuaded someone to adopt your idea or proposal. What was your approach?",
            'follow_ups': ["What objections did you face?", "How did you address them?"],
            'tips': "Look for logical structuring, emotional appeal, and evidence-based reasoning.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time when you had to present to a senior leadership team or board. How did you prepare?",
            'follow_ups': ["What was the most challenging question you received?", "How did the presentation influence the outcome?"],
            'tips': "Assess executive presence, preparation, and ability to handle tough questions under pressure.",
            'levels': ['senior', 'executive'],
        },
        {
            'text': "Tell me about a time when you had to manage communications during a crisis or high-pressure situation.",
            'follow_ups': ["Who were the key stakeholders?", "How did you ensure the right people had the right information at the right time?"],
            'tips': "Look for calm under pressure, clarity, and stakeholder empathy during difficult times.",
            'levels': ['mid', 'senior', 'executive'],
        },
    ],
    'problem_solving': [
        {
            'text': "Describe one of the most challenging problems you've solved at work. Walk me through your thinking process.",
            'follow_ups': ["What data or resources did you use?", "How did you evaluate possible solutions before choosing one?"],
            'tips': "Look for structured thinking, use of data, and iterative approach.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time when you identified a problem before it became critical. How did you spot it and what did you do?",
            'follow_ups': ["What signals or patterns did you notice?", "What was the impact of your early intervention?"],
            'tips': "Assess proactiveness, analytical skills, and business acumen.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of when you had to solve a problem with limited information or resources. What was your approach?",
            'follow_ups': ["How did you prioritize what to do first?", "What assumptions did you make and how did you validate them?"],
            'tips': "Look for resourcefulness, hypothesis-driven thinking, and decisiveness under ambiguity.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time you had to choose between two or more valid solutions. How did you decide?",
            'follow_ups': ["What criteria did you use to evaluate the options?", "Looking back, was it the right choice?"],
            'tips': "Assess decision frameworks, trade-off analysis, and willingness to reflect.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where your initial approach to solving a problem failed. What did you do next?",
            'follow_ups': ["How did you recover?", "What did the failure teach you?"],
            'tips': "Look for resilience, learning mindset, and ability to pivot without losing momentum.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time you had to solve a problem that no one else in your team had encountered before.",
            'follow_ups': ["How did you research or benchmark?", "How did you document the solution for others?"],
            'tips': "Assess curiosity, self-sufficiency, and knowledge sharing.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example where you used data or analytics to solve a business problem.",
            'follow_ups': ["What tools or methods did you use?", "What was the outcome?"],
            'tips': "Look for data literacy, translation from insight to action, and measurable results.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
    ],
    'teamwork': [
        {
            'text': "Tell me about a time you worked in a diverse team with very different working styles. How did you make it work?",
            'follow_ups': ["What was the most significant difference you had to navigate?", "What did you learn about working with diverse styles?"],
            'tips': "Assess flexibility, empathy, and ability to leverage diversity of thought.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time when you had to put the team's needs above your personal preferences or goals. What was the situation?",
            'follow_ups': ["How did that affect you personally?", "What was the team outcome?"],
            'tips': "Look for team-first mindset, selflessness, and collaborative spirit.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time when you disagreed with a team decision. How did you handle it?",
            'follow_ups': ["Did you escalate or accept the decision?", "What was the eventual outcome?"],
            'tips': "Assess ability to disagree professionally and commit to team decisions.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of a project where collaboration across departments was critical to success. What was your role?",
            'follow_ups': ["What were the biggest cross-functional challenges?", "How did you contribute beyond your own responsibilities?"],
            'tips': "Look for cross-functional collaboration skills and going above and beyond.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time when you stepped in to support a struggling teammate. What did you do?",
            'follow_ups': ["How did you balance this with your own workload?", "What was the outcome for both of you?"],
            'tips': "Assess generosity, emotional intelligence, and collaborative spirit.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
    ],
    'adaptability': [
        {
            'text': "Tell me about a time when your priorities changed significantly mid-project. How did you adapt?",
            'follow_ups': ["How did you communicate the change to stakeholders?", "What did you have to sacrifice?"],
            'tips': "Look for flexibility, grace under change, and clear re-prioritization skills.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time when you had to learn a new skill or technology quickly to meet a deadline. How did you approach it?",
            'follow_ups': ["What resources did you use?", "How quickly did you get up to speed?"],
            'tips': "Assess learning agility, resourcefulness, and determination.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a significant organizational change (restructuring, new leadership, pivot) you experienced. How did you navigate it?",
            'follow_ups': ["What was the most challenging aspect of the change?", "How did you support others through it?"],
            'tips': "Look for resilience, positivity during change, and ability to influence culture.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of a time you had to work with a completely new process or system. What challenges did you face?",
            'follow_ups': ["How long did it take to become effective?", "What would have helped you adapt faster?"],
            'tips': "Assess willingness to embrace change and self-directed learning.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time when you had to manage multiple competing priorities simultaneously. How did you stay organized?",
            'follow_ups': ["What tools or systems did you use?", "Did anything fall through the cracks? How did you recover?"],
            'tips': "Look for prioritization frameworks, composure, and proactive communication.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
    ],
    'initiative': [
        {
            'text': "Tell me about a time you identified an opportunity to improve a process or system and took action. What drove you to act?",
            'follow_ups': ["How did you get buy-in from others?", "What was the impact of the improvement?"],
            'tips': "Assess proactiveness, ownership mindset, and impact orientation.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where you went above and beyond your job description to deliver value. What motivated you?",
            'follow_ups': ["Was this recognised by others?", "Would you do it again?"],
            'tips': "Look for discretionary effort, intrinsic motivation, and growth mindset.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of a new idea you championed from concept to execution. What obstacles did you overcome?",
            'follow_ups': ["How did you build momentum?", "What was the outcome?"],
            'tips': "Assess entrepreneurial thinking, persistence, and execution capability.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time you set an ambitious goal for yourself. How did you plan and track progress?",
            'follow_ups': ["Did you achieve it? What helped or hindered you?", "What did the experience teach you about goal-setting?"],
            'tips': "Look for ambition, structured goal-setting, and self-accountability.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
    ],
    'customer_focus': [
        {
            'text': "Tell me about a time you went out of your way to ensure a customer had an exceptional experience.",
            'follow_ups': ["What was your motivation?", "How did the customer respond and what was the business impact?"],
            'tips': "Assess customer empathy, ownership, and the ability to delight stakeholders.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where you received negative feedback from a customer. How did you handle it?",
            'follow_ups': ["What steps did you take to resolve the issue?", "How did you prevent it from happening again?"],
            'tips': "Look for accountability, empathy, and service recovery skills.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time when customer needs conflicted with business or technical constraints. How did you balance them?",
            'follow_ups': ["How did you communicate the constraints to the customer?", "What was the outcome?"],
            'tips': "Assess negotiation, creative problem-solving, and diplomatic communication.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of how you used customer feedback to drive a change or improvement.",
            'follow_ups': ["How did you collect and analyze the feedback?", "What was the measurable impact of the change?"],
            'tips': "Look for voice-of-customer listening, data-driven improvement, and follow-through.",
            'levels': ['mid', 'senior', 'executive'],
        },
    ],
    'analytical_thinking': [
        {
            'text': "Describe a time when you had to analyze a large amount of data to make a business recommendation. Walk me through your process.",
            'follow_ups': ["What tools did you use?", "How did you communicate your findings to stakeholders?"],
            'tips': "Assess analytical rigor, data storytelling, and ability to derive actionable insights.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time when your analysis revealed a counter-intuitive finding. How did you validate it and present it?",
            'follow_ups': ["How did stakeholders react to the unexpected result?", "What action was taken based on your finding?"],
            'tips': "Look for intellectual honesty, validation discipline, and courage to present uncomfortable truths.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of how you broke down a complex business problem into smaller, more manageable parts.",
            'follow_ups': ["How did you sequence the analysis?", "What was the most challenging component?"],
            'tips': "Assess structured thinking, decomposition ability, and focus.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time when you had to make a decision with incomplete data. How did you handle the uncertainty?",
            'follow_ups': ["What assumptions did you make?", "How did you validate them over time?"],
            'tips': "Look for comfort with ambiguity, hypothesis-driven thinking, and risk management.",
            'levels': ['mid', 'senior', 'executive'],
        },
    ],
    'conflict_resolution': [
        {
            'text': "Tell me about a time you had a significant conflict with a colleague. How did you resolve it?",
            'follow_ups': ["What was the root cause of the conflict?", "What did you learn about managing interpersonal differences?"],
            'tips': "Assess emotional intelligence, empathy, and willingness to seek win-win outcomes.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time when you had to mediate a conflict between two team members. What was your approach?",
            'follow_ups': ["How did you remain neutral?", "What was the final outcome?"],
            'tips': "Look for fairness, structured conflict resolution skills, and leadership under tension.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time you had to navigate a disagreement between departments about resources or priorities.",
            'follow_ups': ["How did you build consensus?", "What did you compromise on?"],
            'tips': "Assess negotiation skills, organizational awareness, and collaborative problem-solving.",
            'levels': ['senior', 'executive'],
        },
    ],
    'innovation': [
        {
            'text': "Tell me about the most innovative idea you've contributed to your organization. How did you come up with it?",
            'follow_ups': ["How did you get others excited about it?", "What was the measurable impact?"],
            'tips': "Look for creative thinking, bias for action, and measurable innovation outcomes.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a time when you challenged the status quo and introduced a new way of doing things. What resistance did you face?",
            'follow_ups': ["How did you overcome scepticism?", "What happened after the change was implemented?"],
            'tips': "Assess change leadership, resilience against the old way, and outcome focus.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Give me an example of a time you experimented with a new approach that did not work out. What did you learn?",
            'follow_ups': ["How did you handle the failure?", "Did you try again with a different approach?"],
            'tips': "Look for learning mindset, psychological safety, and iterative thinking.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
    ],
    'integrity': [
        {
            'text': "Tell me about a time when you had to make an ethically difficult decision at work. How did you approach it?",
            'follow_ups': ["What values guided your decision?", "What was the outcome?"],
            'tips': "Assess moral courage, principled decision-making, and willingness to do the right thing even when difficult.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Describe a situation where you were pressured to compromise your standards or values. What did you do?",
            'follow_ups': ["How did the situation resolve?", "Would you handle it the same way again?"],
            'tips': "Look for non-negotiable integrity and the ability to stand firm under pressure.",
            'levels': ['mid', 'senior', 'executive'],
        },
        {
            'text': "Tell me about a time you made a mistake that had a significant impact. How did you handle it?",
            'follow_ups': ["How quickly did you disclose it?", "What did you do to make it right?"],
            'tips': "Assess ownership, transparency, and accountability rather than blame-shifting.",
            'levels': ['junior', 'mid', 'senior', 'executive'],
        },
    ],
}

TECHNICAL_QUESTIONS = {
    'software_engineering': {
        'junior': [
            {'text': "Explain the difference between object-oriented and functional programming paradigms. When would you choose one over the other?", 'follow_ups': ["Can you give an example from your own experience?"]},
            {'text': "What is the time complexity of common sorting algorithms? Which would you use for a list of 10 million items?", 'follow_ups': ["What trade-offs exist between quicksort and mergesort?"]},
            {'text': "How do you approach debugging a production issue you've never seen before?", 'follow_ups': ["What tools do you use?", "How do you communicate status to stakeholders?"]},
            {'text': "Describe your experience with version control systems. How do you handle merge conflicts?", 'follow_ups': ["What's your branching strategy?"]},
            {'text': "What is REST and how does it differ from GraphQL? When would you use each?", 'follow_ups': ["Can you describe a REST API you've built?"]},
        ],
        'mid': [
            {'text': "Walk me through how you would design a scalable URL shortener service. What are the key architectural decisions?", 'follow_ups': ["How would you handle 100 million requests per day?", "What database would you choose and why?"]},
            {'text': "How do you approach designing a microservices architecture versus a monolith? What factors drive your decision?", 'follow_ups': ["What are the biggest operational challenges of microservices?"]},
            {'text': "Describe your approach to writing tests. What is the right balance between unit, integration, and end-to-end tests?", 'follow_ups': ["How do you handle testing for third-party dependencies?"]},
            {'text': "How have you handled performance bottlenecks in production systems? Walk me through a specific example.", 'follow_ups': ["What profiling tools did you use?", "What was the before/after impact?"]},
            {'text': "Explain the CAP theorem and how it influences your database design choices.", 'follow_ups': ["Have you had to make a trade-off between consistency and availability in practice?"]},
        ],
        'senior': [
            {'text': "You are asked to re-architect a legacy monolith to a scalable cloud-native system with zero downtime. How do you approach this?", 'follow_ups': ["How do you manage risk?", "How do you involve the team?"]},
            {'text': "How do you make technology decisions that balance short-term delivery with long-term maintainability?", 'follow_ups': ["How do you quantify technical debt?", "How do you get non-technical stakeholders to invest in it?"]},
            {'text': "Describe your approach to setting technical standards and driving engineering excellence across a team.", 'follow_ups': ["How do you enforce standards without stifling creativity?"]},
            {'text': "Tell me about a time you had to evaluate a build vs. buy decision for a critical component. What was your framework?", 'follow_ups': ["What was the outcome and would you make the same call again?"]},
        ],
        'executive': [
            {'text': "How do you align engineering strategy with business objectives? Can you give a concrete example?", 'follow_ups': ["How do you communicate technical roadmap to the board?"]},
            {'text': "How do you build and retain a world-class engineering organization? What is your talent philosophy?", 'follow_ups': ["How have you handled key engineer attrition?"]},
            {'text': "Describe how you approach cybersecurity and compliance at an organizational level.", 'follow_ups': ["How do you instill a security-first culture?"]},
        ],
    },
    'hr_human_resources': {
        'junior': [
            {'text': "What are the key stages of an employee lifecycle and what HR activities happen at each stage?", 'follow_ups': ["Which stage do you find most complex and why?"]},
            {'text': "How do you approach sourcing passive candidates for a hard-to-fill role?", 'follow_ups': ["What platforms have you found most effective?"]},
            {'text': "Explain the difference between fixed and variable compensation components. How do you communicate total rewards to candidates?", 'follow_ups': []},
            {'text': "What factors do you consider when onboarding a new employee remotely versus in-person?", 'follow_ups': ["How do you measure onboarding effectiveness?"]},
        ],
        'mid': [
            {'text': "How do you design a performance management process that drives both accountability and development?", 'follow_ups': ["How do you handle calibration?", "How do you deal with managers who rate everyone highly?"]},
            {'text': "Walk me through how you have handled a complex employee relations case (e.g., harassment, grievance, misconduct). What was your process?", 'follow_ups': ["How did you ensure confidentiality?", "What was the outcome?"]},
            {'text': "How do you build a strong employer brand to compete for talent against larger organizations?", 'follow_ups': ["What channels or tactics have you used?", "How do you measure EVP impact?"]},
            {'text': "Describe your approach to running a compensation benchmarking exercise. What data sources do you use?", 'follow_ups': ["How do you gain leadership buy-in for salary adjustments?"]},
        ],
        'senior': [
            {'text': "How do you build an HR strategy that supports a company scaling from 200 to 2,000 employees?", 'follow_ups': ["What capabilities do you invest in first?", "How do you keep culture intact at scale?"]},
            {'text': "Describe how you have used people analytics to influence a significant business decision.", 'follow_ups': ["What data did you analyze?", "How did you present it to leadership?"]},
            {'text': "How do you approach workforce planning in a volatile industry? What models or frameworks do you use?", 'follow_ups': ["How far out do you plan and how often do you revisit?"]},
        ],
        'executive': [
            {'text': "How do you ensure HR is seen as a strategic business partner rather than an administrative function?", 'follow_ups': ["How do you measure HR's business impact?"]},
            {'text': "Describe your philosophy on building an inclusive culture. What concrete programmes have you implemented?", 'follow_ups': ["How do you measure inclusion outcomes beyond diversity metrics?"]},
            {'text': "How do you future-proof your talent strategy in the face of automation and AI replacing certain roles?", 'follow_ups': ["What reskilling programmes have you launched?"]},
        ],
    },
    'finance_accounting': {
        'junior': [
            {'text': "Walk me through the three financial statements and how they are interconnected.", 'follow_ups': ["If net income increases by $100, what happens to the balance sheet and cash flow statement?"]},
            {'text': "What is the difference between accounts payable and accounts receivable? How do you manage both effectively?", 'follow_ups': []},
            {'text': "Explain the concept of accrual accounting versus cash-basis accounting. When is each appropriate?", 'follow_ups': []},
            {'text': "How do you ensure accuracy when performing month-end close? What checks do you put in place?", 'follow_ups': []},
        ],
        'mid': [
            {'text': "Walk me through how you would build a financial model for a new product launch. What assumptions would you stress-test?", 'follow_ups': ["How do you present sensitivity analysis to non-finance stakeholders?"]},
            {'text': "How have you approached variance analysis when actuals significantly differ from budget? What actions do you take?", 'follow_ups': ["How do you prevent the same variance from recurring?"]},
            {'text': "Describe your experience with internal controls. How have you identified and remediated a control weakness?", 'follow_ups': []},
            {'text': "How do you prioritize capital allocation when multiple business units are competing for budget?", 'follow_ups': ["What frameworks or criteria do you use?"]},
        ],
        'senior': [
            {'text': "How do you build a financial planning process that is both rigorous and agile enough to respond to market changes?", 'follow_ups': ["How do you balance top-down targets with bottom-up inputs?"]},
            {'text': "Tell me about a time you identified a significant financial risk and took preventive action. What was the outcome?", 'follow_ups': ["How did you quantify the risk?", "How did you communicate it to the board?"]},
            {'text': "How have you led or managed an audit (internal or external)? What was your approach to preparation and relationship management?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you balance the tension between investing for growth and maintaining financial discipline?", 'follow_ups': ["How do you frame this trade-off for your board?"]},
            {'text': "Describe your approach to capital structure decisions. How do you determine the right mix of debt and equity?", 'follow_ups': []},
            {'text': "How do you build a finance function that is both a control centre and a strategic partner to the business?", 'follow_ups': []},
        ],
    },
    'marketing_digital': {
        'junior': [
            {'text': "What is the difference between paid, owned, and earned media? Give an example of each.", 'follow_ups': []},
            {'text': "How do you measure the success of a social media campaign? What KPIs do you track?", 'follow_ups': ["How do you attribute social media impact to revenue?"]},
            {'text': "Walk me through how you would set up a Google Ads campaign for a new product launch.", 'follow_ups': ["How do you structure ad groups and keywords?"]},
            {'text': "What is SEO, and what are the most important on-page and off-page factors you focus on?", 'follow_ups': []},
        ],
        'mid': [
            {'text': "How do you build a content marketing strategy that drives qualified leads rather than just traffic?", 'follow_ups': ["How do you align content to the buyer journey?", "How do you measure content ROI?"]},
            {'text': "Describe a full-funnel marketing campaign you have executed. What was the strategy and how did you measure impact?", 'follow_ups': ["What channels did you use?", "What would you do differently?"]},
            {'text': "How do you use data and analytics to optimize a marketing programme in flight? Give me a specific example.", 'follow_ups': ["What tools did you use?", "What signal triggered the change?"]},
            {'text': "How do you approach market segmentation and persona development for a new product?", 'follow_ups': []},
        ],
        'senior': [
            {'text': "How do you build a brand strategy that resonates emotionally while driving measurable commercial outcomes?", 'follow_ups': ["How do you measure brand equity?"]},
            {'text': "Tell me how you have structured a marketing team and budget across channels for a growth-stage company.", 'follow_ups': ["How did you allocate spend across awareness, consideration, and conversion?"]},
            {'text': "Describe your experience with marketing technology stacks. How do you evaluate and integrate new tools?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you build a customer acquisition strategy that scales efficiently? What is your unit economics framework?", 'follow_ups': ["At what CAC:LTV ratio do you consider a channel viable?"]},
            {'text': "Describe how you align marketing strategy to overall business strategy and communicate it to the board.", 'follow_ups': []},
            {'text': "How have you managed marketing through an economic downturn? How do you protect and justify the marketing budget?", 'follow_ups': []},
        ],
    },
    'sales_business_development': {
        'junior': [
            {'text': "Walk me through your typical process for qualifying a new sales prospect.", 'follow_ups': ["What criteria do you use?", "What qualifying frameworks have you used (BANT, MEDDIC, etc.)?"]},
            {'text': "Tell me about the most successful deal you have closed. What made it successful?", 'follow_ups': ["What challenges did you overcome?", "What did you learn?"]},
            {'text': "How do you handle objections from a prospect who says your price is too high?", 'follow_ups': ["What is your approach to value-based selling?"]},
            {'text': "How do you stay motivated through a long, complex sales cycle with a prospect who goes quiet?", 'follow_ups': []},
        ],
        'mid': [
            {'text': "How do you approach building a territory or account plan? Walk me through your process.", 'follow_ups': ["How do you prioritize which accounts to focus on?"]},
            {'text': "Tell me about a time you lost a major deal. What did you learn and how did you apply it?", 'follow_ups': ["Did you do a formal win/loss review?"]},
            {'text': "Describe your experience selling to the C-suite. How do you gain access and build executive relationships?", 'follow_ups': ["What is your approach to executive engagement?"]},
            {'text': "How do you manage a complex, multi-stakeholder deal with competing interests inside the buying organization?", 'follow_ups': ["How do you identify the economic buyer?"]},
        ],
        'senior': [
            {'text': "How do you build and coach a high-performing sales team? What is your leadership philosophy?", 'follow_ups': ["How do you identify and develop top performers?", "How do you manage underperformers?"]},
            {'text': "Tell me about a time you expanded a key account significantly. What was your strategy?", 'follow_ups': ["How did you build the business case for expansion?"]},
            {'text': "How do you structure sales compensation to motivate the right behaviours and outcomes?", 'follow_ups': ["How do you prevent commission gaming?"]},
        ],
        'executive': [
            {'text': "How do you build a go-to-market strategy for entering a new market or segment?", 'follow_ups': ["What signals tell you a market is ready?"]},
            {'text': "How do you align sales, marketing, and product teams to drive cohesive revenue growth?", 'follow_ups': []},
            {'text': "Tell me about a time you transformed a sales organisation. What drove the change and how did you manage it?", 'follow_ups': []},
        ],
    },
    'operations_supply_chain': {
        'junior': [
            {'text': "What is the difference between push and pull inventory management strategies? When do you use each?", 'follow_ups': []},
            {'text': "Explain the concept of lead time and cycle time. How do you reduce them?", 'follow_ups': []},
            {'text': "What is Six Sigma and how have you applied lean principles in your work?", 'follow_ups': []},
            {'text': "How do you handle supplier quality issues? Walk me through your escalation process.", 'follow_ups': []},
        ],
        'mid': [
            {'text': "Describe a process improvement initiative you led. What methodology did you use and what was the outcome?", 'follow_ups': ["How did you measure success?", "How did you sustain the improvement?"]},
            {'text': "How do you manage supply chain risk? Give me an example of a risk event you navigated.", 'follow_ups': ["What mitigation strategies did you put in place?"]},
            {'text': "Tell me how you have used data and KPIs to manage operational performance. What metrics do you focus on?", 'follow_ups': []},
            {'text': "How have you managed cost reduction programmes without sacrificing quality or service levels?", 'follow_ups': []},
        ],
        'senior': [
            {'text': "How do you design an operations strategy that supports rapid business growth? What capabilities do you invest in first?", 'follow_ups': []},
            {'text': "Tell me about a time you led a significant operational transformation (e.g., ERP implementation, outsourcing, automation). What was your approach?", 'follow_ups': ["How did you manage change resistance?"]},
            {'text': "How do you build supplier relationships that create competitive advantage rather than just cost savings?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you build a global supply chain that is resilient, sustainable, and cost-efficient?", 'follow_ups': ["How do you balance these three competing objectives?"]},
            {'text': "Describe how you have applied digital transformation (IoT, AI, automation) to operations.", 'follow_ups': []},
            {'text': "How do you align operations strategy with business strategy and communicate it to the board?", 'follow_ups': []},
        ],
    },
    'data_science_analytics': {
        'junior': [
            {'text': "Explain the difference between supervised and unsupervised learning. Give an example use case for each.", 'follow_ups': []},
            {'text': "What is overfitting and how do you detect and prevent it?", 'follow_ups': ["What is the bias-variance trade-off?"]},
            {'text': "Walk me through your approach to exploratory data analysis (EDA) on a new dataset.", 'follow_ups': ["What tools and visualizations do you use?"]},
            {'text': "How do you handle missing data in a dataset? What are the trade-offs of different imputation strategies?", 'follow_ups': []},
            {'text': "Explain how you would evaluate the performance of a classification model. What metrics matter most?", 'follow_ups': ["When would you prioritize precision over recall?"]},
        ],
        'mid': [
            {'text': "Describe the architecture of an end-to-end machine learning pipeline you have built. What were the key challenges?", 'follow_ups': ["How did you handle model drift over time?"]},
            {'text': "How do you communicate the output and confidence intervals of a model to a non-technical business audience?", 'follow_ups': ["Give an example of a model recommendation that changed a business decision."]},
            {'text': "Tell me about a time you built a recommendation system. What algorithm did you choose and why?", 'follow_ups': ["How did you evaluate recommendation quality?"]},
            {'text': "How do you approach feature engineering? What is your process for selecting and transforming variables?", 'follow_ups': []},
        ],
        'senior': [
            {'text': "How do you build a data science function from scratch? What do you prioritize in the first 90 days?", 'follow_ups': ["How do you prove value quickly?"]},
            {'text': "How do you ensure responsible AI and manage bias in your models?", 'follow_ups': ["What governance processes do you put in place?"]},
            {'text': "Tell me about the most impactful analytical work you have done. How did it change the business?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you build a data strategy that unlocks competitive advantage?", 'follow_ups': ["How do you ensure data governance and privacy?"]},
            {'text': "How do you build a culture of data-driven decision-making in an organisation that relies on gut instinct?", 'follow_ups': []},
            {'text': "What is your vision for how AI will reshape the business over the next 3-5 years?", 'follow_ups': []},
        ],
    },
    'product_management': {
        'junior': [
            {'text': "How do you prioritize a product backlog when you have more requests than capacity? What framework do you use?", 'follow_ups': ["How do you handle stakeholder disagreement over priorities?"]},
            {'text': "Tell me about a time you gathered user feedback and translated it into product requirements.", 'follow_ups': ["What methods did you use to gather feedback?"]},
            {'text': "What is the difference between a product roadmap and a product backlog? How do you keep them aligned?", 'follow_ups': []},
            {'text': "How do you define and measure the success of a new product feature?", 'follow_ups': ["What metrics do you set before launch?"]},
        ],
        'mid': [
            {'text': "Tell me about the most successful product feature you shipped. How did you define it, build it, and measure success?", 'follow_ups': ["What would you do differently?"]},
            {'text': "How do you work with engineering teams to balance feature development with technical debt reduction?", 'follow_ups': ["How do you communicate technical trade-offs to business stakeholders?"]},
            {'text': "How do you validate a product idea before investing significant engineering resources?", 'follow_ups': ["What discovery techniques do you use?", "Tell me about a hypothesis that was proven wrong."]},
            {'text': "Describe a time you had to kill a feature or project. How did you make that decision and communicate it?", 'follow_ups': []},
        ],
        'senior': [
            {'text': "How do you set a product vision and strategy and get the entire organisation aligned behind it?", 'follow_ups': ["How do you revisit and update the vision?"]},
            {'text': "Tell me how you have managed product strategy across a portfolio of products or a platform.", 'follow_ups': ["How do you prevent cannibalisation?"]},
            {'text': "How do you think about competitive positioning? How do you ensure your product stays ahead?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you build a product organisation that delivers continuous innovation at scale?", 'follow_ups': []},
            {'text': "How do you balance long-term product vision with short-term business pressure?", 'follow_ups': ["Give me a concrete example of this tension."]},
            {'text': "How do you think about monetisation strategy and pricing for your product portfolio?", 'follow_ups': []},
        ],
    },
    'customer_service': {
        'junior': [
            {'text': "How do you handle an angry or frustrated customer who is demanding a refund or resolution you are not authorised to give?", 'follow_ups': ["What is your de-escalation technique?"]},
            {'text': "What does excellent customer service look like to you? Give me an example of when you delivered it.", 'follow_ups': []},
            {'text': "How do you manage a high volume of enquiries while maintaining quality and response time?", 'follow_ups': []},
            {'text': "Tell me about a time you turned a negative customer experience into a positive one.", 'follow_ups': []},
        ],
        'mid': [
            {'text': "How do you use customer satisfaction data (CSAT, NPS) to identify and address systemic issues?", 'follow_ups': ["Give me a specific example."]},
            {'text': "Describe how you have coached a team to improve customer service quality. What metrics improved?", 'follow_ups': []},
            {'text': "How do you balance self-service and automation with the need for human interaction in customer support?", 'follow_ups': []},
        ],
        'senior': [
            {'text': "How do you build a customer experience strategy that differentiates your brand?", 'follow_ups': []},
            {'text': "Tell me about a time you transformed a customer service operation. What were the biggest obstacles?", 'follow_ups': []},
            {'text': "How do you measure and reduce customer churn? What proactive strategies have you implemented?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you embed a customer-centric culture across an entire organisation, not just the support team?", 'follow_ups': []},
            {'text': "How do you think about the future of customer experience with AI and automation? What is your vision?", 'follow_ups': []},
        ],
    },
    'general_management': {
        'mid': [
            {'text': "How do you prioritize as a manager when everything feels urgent? Walk me through your framework.", 'follow_ups': []},
            {'text': "Tell me about the hardest performance conversation you've had as a manager. How did you prepare and what happened?", 'follow_ups': []},
        ],
        'senior': [
            {'text': "How do you build a high-performing team culture? What specific actions do you take?", 'follow_ups': ["How do you maintain culture during rapid growth?"]},
            {'text': "Describe how you manage the tension between short-term results and long-term investment.", 'follow_ups': []},
            {'text': "Tell me about a time you had to make a significant organizational change. How did you plan and execute it?", 'follow_ups': []},
        ],
        'executive': [
            {'text': "How do you develop and communicate a company strategy to diverse stakeholders — employees, board, customers, investors?", 'follow_ups': []},
            {'text': "Describe a time when you had to make a bet-the-company decision. How did you approach it?", 'follow_ups': ["What was the outcome and what did you learn?"]},
            {'text': "How do you build a leadership team that is greater than the sum of its parts?", 'follow_ups': []},
            {'text': "How do you balance being decisive with being inclusive in your leadership style?", 'follow_ups': []},
        ],
    },
}

SITUATIONAL_QUESTIONS = [
    {
        'text': "Imagine you discover that a key project deadline will be missed with two weeks to go. What do you do in the first 24 hours?",
        'follow_ups': ["How do you communicate this to leadership?", "What do you do to minimize the impact?"],
        'tips': "Assess accountability, crisis communication, and problem-solving under pressure.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "You have been asked to implement a process you believe is inefficient and could be done better. Your manager insists on the current approach. How do you handle this?",
        'follow_ups': ["At what point do you escalate vs. comply?"],
        'tips': "Look for ability to advocate for better ideas while respecting authority and team cohesion.",
        'levels': ['junior', 'mid', 'senior'],
    },
    {
        'text': "Two of your team members are in ongoing conflict that is affecting the team's output. You have tried to resolve it informally without success. What are your next steps?",
        'follow_ups': ["How do you prevent this from affecting others on the team?"],
        'tips': "Assess conflict escalation judgment, HR partnership, and leadership responsibility.",
        'levels': ['mid', 'senior', 'executive'],
    },
    {
        'text': "You are given a 20% budget cut mid-year. How do you decide what to cut and how do you communicate it to your team?",
        'follow_ups': ["How do you protect the highest-value activities?"],
        'tips': "Look for strategic prioritization, financial acumen, and transparent communication.",
        'levels': ['mid', 'senior', 'executive'],
    },
    {
        'text': "A star performer on your team has become a flight risk after being passed over for promotion. What do you do?",
        'follow_ups': ["How do you make the retention conversation?", "If they leave, what do you do differently next time?"],
        'tips': "Assess retention strategies, empathy, and the ability to have difficult career conversations.",
        'levels': ['mid', 'senior', 'executive'],
    },
    {
        'text': "You are new to a role and quickly realize the team's current approach is outdated. How do you drive change while respecting existing relationships and institutional knowledge?",
        'follow_ups': ["How fast do you move?", "Who do you bring along first?"],
        'tips': "Look for a balance of listening, humility, and decisive change leadership.",
        'levels': ['mid', 'senior', 'executive'],
    },
    {
        'text': "You discover that a colleague has been taking credit for work done by members of your team. How do you address it?",
        'follow_ups': ["Do you go directly to the colleague, your manager, or HR?"],
        'tips': "Assess judgment, courage, and fairness in navigating workplace politics.",
        'levels': ['junior', 'mid', 'senior'],
    },
    {
        'text': "You are leading a project and a key dependency from another team is significantly delayed. What do you do?",
        'follow_ups': ["How do you protect your timeline?", "How do you manage the other team's stakeholders?"],
        'tips': "Look for proactiveness, cross-functional influence, and contingency planning.",
        'levels': ['junior', 'mid', 'senior'],
    },
    {
        'text': "Your top client is threatening to leave because of a service issue not directly caused by your team. How do you handle it?",
        'follow_ups': ["What do you do in the short term to stop the bleeding?", "What long-term changes do you make?"],
        'tips': "Assess customer ownership, cross-functional coordination, and recovery planning.",
        'levels': ['mid', 'senior', 'executive'],
    },
    {
        'text': "You are asked to deliver a project in half the usual time with the same scope and quality. How do you respond and what do you do?",
        'follow_ups': ["What trade-offs do you propose?", "How do you keep the team motivated through the crunch?"],
        'tips': "Look for scope negotiation skills, resourcefulness, and realistic commitment-making.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
]

OPENING_QUESTIONS = [
    {
        'text': "Tell me about yourself and your career journey that has led you to apply for this role.",
        'follow_ups': ["What has been the defining moment in your career so far?"],
        'tips': "Assess communication clarity, self-awareness, and relevance of experience to this role.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "What attracted you specifically to this company and this role? What do you know about us?",
        'follow_ups': ["What aspect of our business excites you most?"],
        'tips': "Look for genuine research, alignment to company mission, and specific knowledge.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "What are you looking for in your next role that your current or most recent role does not offer?",
        'follow_ups': ["How does this role address that gap?"],
        'tips': "Assess motivation, career intentionality, and self-awareness about gaps.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "How would your current (or most recent) manager describe you — both your strengths and areas for development?",
        'follow_ups': ["Is that how you would describe yourself?"],
        'tips': "Assess self-awareness, honesty, and alignment between self-perception and external perception.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "What is your greatest professional achievement, and why does it stand out to you?",
        'follow_ups': ["What impact did it have on the business?"],
        'tips': "Look for scale of impact, ownership, and alignment to this role's requirements.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
]

CULTURE_FIT_QUESTIONS = [
    {
        'text': "What type of work environment brings out the best in you? How do you perform when the environment is different from your ideal?",
        'follow_ups': ["How do you adapt?"],
        'tips': "Assess self-awareness and flexibility to thrive in different conditions.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "How do you balance achieving ambitious results with maintaining your team's wellbeing and work-life balance?",
        'follow_ups': ["Give a specific example."],
        'tips': "Assess values alignment around people-first leadership and sustainable high performance.",
        'levels': ['mid', 'senior', 'executive'],
    },
    {
        'text': "Describe the culture of the best team you have ever worked in. What made it great?",
        'follow_ups': ["How did you contribute to that culture?"],
        'tips': "Look for cultural fit signals and understanding of what drives great teams.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "How do you continue learning and growing professionally? What have you learned in the past year?",
        'follow_ups': ["How do you apply what you learn?"],
        'tips': "Assess growth mindset, intellectual curiosity, and commitment to continuous development.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "What do you believe are the most important qualities of a successful employee in a fast-growing organisation?",
        'follow_ups': ["How do you demonstrate those qualities?"],
        'tips': "Assess growth mindset, ambiguity tolerance, and alignment to a high-performance culture.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "Tell me about a time when your values were tested at work. How did you respond?",
        'follow_ups': ["Would you make the same choice again?"],
        'tips': "Assess integrity, values clarity, and moral courage.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "What does diversity, equity, and inclusion mean to you, and how have you contributed to a more inclusive environment?",
        'follow_ups': ["Give a concrete example."],
        'tips': "Assess genuine commitment to DEI and the ability to create belonging for others.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
    {
        'text': "How do you give and receive feedback? Can you share an example of critical feedback that changed how you work?",
        'follow_ups': ["How quickly did you implement the feedback?"],
        'tips': "Assess openness to feedback, coachability, and growth orientation.",
        'levels': ['junior', 'mid', 'senior', 'executive'],
    },
]

# ───────────────────────────────────────────────────────────────
# ROLE KEYWORD → DOMAIN MAPPING
# ───────────────────────────────────────────────────────────────

ROLE_KEYWORDS = {
    'software_engineering': [
        'software', 'engineer', 'developer', 'programmer', 'coder', 'backend', 'frontend',
        'fullstack', 'full-stack', 'devops', 'sre', 'cloud', 'architect', 'qa', 'test',
        'mobile', 'ios', 'android', 'web', 'api', 'platform', 'infrastructure', 'data engineer',
        'machine learning', 'ml engineer', 'ai engineer', 'tech lead', 'cto',
    ],
    'hr_human_resources': [
        'hr', 'human resources', 'talent', 'people', 'recruiter', 'recruiting', 'recruitment',
        'hrbp', 'hr business partner', 'learning', 'development', 'l&d', 'payroll',
        'compensation', 'benefits', 'employee', 'culture', 'engagement', 'chro',
        'people operations', 'people ops', 'workforce',
    ],
    'finance_accounting': [
        'finance', 'financial', 'accounting', 'accountant', 'cfo', 'controller', 'cpa',
        'audit', 'auditor', 'tax', 'treasury', 'fp&a', 'analyst', 'budget', 'commercial',
        'investment', 'credit', 'risk', 'compliance',
    ],
    'marketing_digital': [
        'marketing', 'digital', 'brand', 'content', 'seo', 'sem', 'paid media', 'social media',
        'demand generation', 'growth', 'product marketing', 'communications', 'pr',
        'public relations', 'email marketing', 'cmo', 'creative', 'copywriter',
    ],
    'sales_business_development': [
        'sales', 'business development', 'account', 'revenue', 'bdr', 'sdr', 'ae',
        'account executive', 'account manager', 'vp sales', 'cro', 'partnerships',
        'enterprise sales', 'inside sales',
    ],
    'operations_supply_chain': [
        'operations', 'supply chain', 'logistics', 'procurement', 'purchasing', 'warehouse',
        'manufacturing', 'production', 'quality', 'lean', 'six sigma', 'process',
        'facilities', 'coo', 'operational',
    ],
    'data_science_analytics': [
        'data science', 'data scientist', 'data analyst', 'analytics', 'bi', 'business intelligence',
        'machine learning', 'deep learning', 'ai', 'artificial intelligence', 'nlp',
        'computer vision', 'statistician', 'quantitative', 'research scientist',
    ],
    'product_management': [
        'product', 'product manager', 'product owner', 'pm', 'cpo', 'product lead',
        'product director', 'program manager', 'project manager', 'scrum',
    ],
    'customer_service': [
        'customer service', 'customer success', 'customer support', 'support', 'cx',
        'customer experience', 'client', 'help desk', 'service desk', 'contact centre',
        'call centre',
    ],
    'general_management': [
        'general manager', 'gm', 'managing director', 'md', 'ceo', 'president', 'chief',
        'vp', 'vice president', 'director', 'head of', 'division',
    ],
}

# ───────────────────────────────────────────────────────────────
# GENERATION ENGINE
# ───────────────────────────────────────────────────────────────

def _detect_role_domain(job_title: str) -> str:
    title_lower = job_title.lower()
    scores = {}
    for domain, keywords in ROLE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in title_lower)
        if score:
            scores[domain] = score
    if not scores:
        return 'general_management'
    return max(scores, key=scores.get)


def _generate_questions(
    job_title: str,
    experience_level: str,
    competencies: list,
    question_types: list,
    count: int,
    company_context: str = '',
    industry: str = '',
) -> list:
    """
    Generate a diverse set of interview questions based on the provided parameters.
    Returns a list of question dicts with metadata.
    """
    rng = random.Random()
    domain = _detect_role_domain(job_title)
    level = experience_level or 'mid'

    question_types_set = set(question_types) if question_types else {
        'behavioral', 'technical', 'situational', 'opening', 'culture_fit'
    }

    result = []
    used_texts = set()

    def _add(q, q_type, competency=''):
        if q['text'] in used_texts:
            return False
        if level not in q.get('levels', [level]):
            return False
        used_texts.add(q['text'])
        result.append({
            'id': len(result) + 1,
            'text': q['text'],
            'type': q_type,
            'competency': competency,
            'follow_ups': q.get('follow_ups', []),
            'tips': q.get('tips', ''),
            'level': level,
        })
        return True

    # 1. OPENING questions (1-2)
    if 'opening' in question_types_set:
        opening_pool = [q for q in OPENING_QUESTIONS if level in q.get('levels', [level])]
        rng.shuffle(opening_pool)
        for q in opening_pool[:2]:
            _add(q, 'opening', 'Opening')

    # 2. BEHAVIORAL / COMPETENCY questions
    if 'behavioral' in question_types_set or 'competency' in question_types_set:
        selected_competencies = competencies if competencies else list(BEHAVIORAL_QUESTIONS.keys())
        rng.shuffle(selected_competencies)

        per_competency = max(1, min(3, (count - len(result)) // max(len(selected_competencies), 1)))
        for comp in selected_competencies:
            pool = [q for q in BEHAVIORAL_QUESTIONS.get(comp, []) if level in q.get('levels', [level])]
            if not pool:
                pool = BEHAVIORAL_QUESTIONS.get(comp, [])
            rng.shuffle(pool)
            added = 0
            for q in pool:
                if _add(q, 'behavioral', comp.replace('_', ' ').title()):
                    added += 1
                    if added >= per_competency:
                        break

    # 3. TECHNICAL questions
    if 'technical' in question_types_set:
        tech_domain_data = TECHNICAL_QUESTIONS.get(domain, {})
        tech_pool = list(tech_domain_data.get(level, []))
        if not tech_pool:
            for lvl in ['mid', 'senior', 'junior', 'executive']:
                tech_pool = list(tech_domain_data.get(lvl, []))
                if tech_pool:
                    break
        rng.shuffle(tech_pool)
        tech_target = max(2, count // 4)
        added = 0
        for q in tech_pool:
            if _add({**q, 'levels': [level], 'tips': q.get('tips', f'Role-specific technical question for {job_title}.')}, 'technical', 'Technical'):
                added += 1
                if added >= tech_target:
                    break

    # 4. SITUATIONAL questions
    if 'situational' in question_types_set:
        sit_pool = [q for q in SITUATIONAL_QUESTIONS if level in q.get('levels', [level])]
        rng.shuffle(sit_pool)
        sit_target = max(1, count // 5)
        added = 0
        for q in sit_pool:
            if _add(q, 'situational', 'Situational'):
                added += 1
                if added >= sit_target:
                    break

    # 5. CULTURE FIT questions
    if 'culture_fit' in question_types_set:
        cf_pool = [q for q in CULTURE_FIT_QUESTIONS if level in q.get('levels', [level])]
        rng.shuffle(cf_pool)
        cf_target = max(1, count // 6)
        added = 0
        for q in cf_pool:
            if _add(q, 'culture_fit', 'Culture Fit'):
                added += 1
                if added >= cf_target:
                    break

    # Trim or pad to requested count
    if len(result) > count:
        result = result[:count]

    # Renumber
    for i, q in enumerate(result):
        q['id'] = i + 1

    return result


# ───────────────────────────────────────────────────────────────
# AI GENERATION (Claude API + DuckDuckGo web search)
# ───────────────────────────────────────────────────────────────

def _get_claude_api_key():
    try:
        return request.env['ir.config_parameter'].sudo().get_param('hrsd.claude_api_key', '') or ''
    except Exception:
        return ''


# ── Question-extraction helpers ──────────────────────────────────

# Patterns that look like a question in scraped text
_Q_PATTERNS = [
    re.compile(r'(?:^|\n)\s*(?:\d+[.)]\s+|Q\s*\d*[.:]\s*|Question\s*\d*[.:]\s*)([^\n?]{15,120}\?)', re.M),
    re.compile(r'([A-Z][^.!?\n]{20,120}\?\s*(?:\n|$))'),
]

# Words that indicate a snippet is NOT a question (ads, navigation, etc.)
_NOISE_WORDS = {'subscribe', 'cookie', 'privacy', 'terms', 'login', 'sign up', 'download', 'click here'}


def _extract_questions_from_text(text: str) -> list:
    """Pull question strings out of free text from web snippets."""
    found = []
    seen = set()
    for pat in _Q_PATTERNS:
        for m in pat.finditer(text):
            q = m.group(1).strip().rstrip('.')
            key = q.lower()[:80]
            if key in seen:
                continue
            if any(w in key for w in _NOISE_WORDS):
                continue
            if len(q) < 20 or q.count(' ') < 3:
                continue
            seen.add(key)
            found.append(q if q.endswith('?') else q + '?')
    return found


def _fetch_page_questions(url: str, max_q: int = 30) -> list:
    """
    Fetch a web page and extract interview questions from it.
    Returns a list of dicts with 'text' and optional 'answer'.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as exc:
        _logger.debug('Page fetch failed %s: %s', url, exc)
        return []

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        questions = []
        seen = set()

        for tag in soup.find_all(['h2', 'h3', 'h4', 'strong', 'b', 'li', 'p']):
            text = tag.get_text(' ', strip=True)
            if '?' not in text or not (20 < len(text) < 300):
                continue
            m = re.search(r'([A-Z][^?]{15,200}\?)', text)
            if not m:
                continue
            q_text = m.group(1).strip()
            key = q_text.lower()[:60]
            if key in seen or any(w in key for w in _NOISE_WORDS) or q_text.count(' ') < 3:
                continue
            seen.add(key)

            # Try to extract a short answer from next sibling element
            answer = ''
            nxt = tag.find_next_sibling()
            if nxt:
                ans = nxt.get_text(' ', strip=True)
                if 20 < len(ans) < 500 and '?' not in ans[:30]:
                    answer = ans[:300]

            questions.append({'text': q_text, 'answer': answer})
            if len(questions) >= max_q:
                break

        return questions
    except Exception as exc:
        _logger.debug('Page parse error %s: %s', url, exc)
        return []


def _skill_based_questions(skills: list, job_title: str, level: str, question_types: list) -> list:
    """
    Build questions from a list of role-specific skills.
    This is the template layer that runs when web scraping doesn't yield
    enough real questions.
    """
    level_desc = {'junior': 'basic', 'mid': 'intermediate', 'senior': 'advanced', 'executive': 'strategic'}
    lvl = level_desc.get(level, 'intermediate')

    templates = {
        'technical': [
            "Explain how you use {skill} in your day-to-day work as a {title}.",
            "Describe a complex problem you solved using {skill}. What was your approach?",
            "What are the best practices you follow when working with {skill}?",
            "How does {skill} integrate with the other tools in a {title}'s workflow?",
            "Walk me through an {lvl}-level {skill} challenge you faced and how you resolved it.",
        ],
        'behavioral': [
            "Tell me about a time when your knowledge of {skill} made a critical difference on a project.",
            "Describe a situation where you had to quickly learn or deepen your expertise in {skill}.",
            "Give an example of when you mentored someone on {skill}.",
        ],
        'situational': [
            "You are asked to design a solution using {skill} under a tight deadline. How do you approach it?",
            "A stakeholder challenges your {skill}-based design decision. How do you respond?",
        ],
    }

    result = []
    rng = random.Random()
    used = set()

    for skill in skills:
        q_type = 'technical' if 'technical' in question_types else (question_types[0] if question_types else 'technical')
        pool = templates.get(q_type, templates['technical'])
        rng.shuffle(pool)
        for tpl in pool:
            text = tpl.format(skill=skill, title=job_title, lvl=lvl)
            if text not in used:
                used.add(text)
                result.append({
                    'text': text,
                    'type': q_type,
                    'competency': skill,
                    'follow_ups': [
                        f"What challenges did you face specifically with {skill}?",
                        "How would you improve your approach if you did it again?",
                    ],
                    'tips': f"Look for concrete experience with {skill} relevant to the {job_title} role at {lvl} level.",
                    'ddg': True,
                })
                break

    return result


# ── Main DuckDuckGo generation function ──────────────────────────

def _classify_q_type(text: str, active_types: set) -> str:
    t = text.lower()
    if any(w in t for w in ('tell me about a time', 'describe a situation', 'give me an example',
                             'how did you', 'walk me through a time')):
        return 'behavioral' if 'behavioral' in active_types else 'technical'
    if any(w in t for w in ('you are', 'imagine you', 'what would you do', 'how would you handle',
                             'suppose you', 'if you were')):
        return 'situational' if 'situational' in active_types else 'technical'
    return 'technical'


def _generate_questions_ddg(job_title, experience_level, competencies, question_types,
                             count, company_context, industry):
    """
    Generate role-specific interview questions using DuckDuckGo web search
    + actual page fetching with BeautifulSoup.

    Flow:
      1. DDG search → get URLs of interview-question pages
      2. Fetch top pages → extract real Q&A pairs from HTML
      3. Supplement with skill-keyword templates if page count is low
      4. Add opening/culture-fit from static bank if needed
      5. Return structured question list

    No AI model needed. RAM: ~60 MB. Speed: 8–20 s.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            _logger.warning('ddgs package not installed; skipping DDG path. Run: pip install ddgs')
            return []

    rng = random.Random()
    industry_tag = f' {industry}' if industry else ''
    active_types = set(question_types or ['technical', 'behavioral', 'situational'])

    # ── Phase 1: DDG search for interview-question pages ─────────
    page_urls = []
    search_queries = [
        f'{job_title}{industry_tag} interview questions answers',
        f'{job_title} technical interview questions',
    ]
    try:
        for query in search_queries:
            results = list(DDGS().text(query, max_results=5))
            for r in results:
                url = r.get('href') or r.get('url', '')
                if url and url not in page_urls:
                    page_urls.append(url)
            if len(page_urls) >= 6:
                break
    except Exception as exc:
        _logger.info('DDG search failed (%s); will use skill-template fallback', exc)

    # ── Phase 2: fetch pages and extract Q&A ─────────────────────
    raw_items = []   # list of {'text': str, 'answer': str}
    seen_keys = set()

    for url in page_urls[:3]:
        items = _fetch_page_questions(url, max_q=25)
        for item in items:
            key = item['text'].lower()[:60]
            if key not in seen_keys and item['text'].count(' ') >= 3:
                seen_keys.add(key)
                raw_items.append(item)
        if len(raw_items) >= count * 2:
            break

    # ── Phase 3: convert to structured question dicts ─────────────
    structured = []
    for item in raw_items:
        q_text = item['text']
        answer  = item.get('answer', '')
        q_type  = _classify_q_type(q_text, active_types)
        if q_type not in active_types:
            q_type = 'technical'

        follow_ups = [
            'Can you give a specific example from your own experience?',
            'What was the outcome and what would you do differently next time?',
        ]
        tips = (
            f'Look for concrete, role-specific experience with {job_title}. '
            'Strong candidates cite tools, metrics, or specific scenarios.'
        )
        if answer:
            tips = f'Expected answer context: {answer[:200]}  |  ' + tips

        structured.append({
            'text': q_text,
            'type': q_type,
            'competency': job_title,
            'follow_ups': follow_ups,
            'tips': tips,
            'ddg': True,
        })

    rng.shuffle(structured)

    # ── Phase 4: skill-keyword template top-up ───────────────────
    skill_keywords = list(competencies) if competencies else []
    if len(structured) < count and not skill_keywords:
        # Try to pull skill keywords from DDG
        try:
            skill_results = list(DDGS().text(
                f'{job_title} key skills technologies responsibilities', max_results=3
            ))
            skill_text = ' '.join(r.get('body', '') for r in skill_results)
            skill_keywords = list(dict.fromkeys(
                m.group(0) for m in re.finditer(
                    r'\b[A-Z][a-zA-Z0-9/._+-]{2,30}(?:\s[A-Z][a-zA-Z0-9/._+-]{2,20}){0,2}\b',
                    skill_text
                )
            ))[:12]
        except Exception:
            pass

    if len(structured) < count and skill_keywords:
        extra = _skill_based_questions(skill_keywords, job_title, experience_level, list(active_types))
        rng.shuffle(extra)
        for e in extra:
            key = e['text'].lower()[:60]
            if key not in seen_keys:
                seen_keys.add(key)
                structured.append(e)
            if len(structured) >= count:
                break

    # ── Phase 5: opening / culture-fit from static bank ──────────
    if 'opening' in active_types and len(structured) < count:
        pool = [q for q in OPENING_QUESTIONS if experience_level in q.get('levels', [experience_level])]
        rng.shuffle(pool)
        for q in pool:
            key = q['text'].lower()[:60]
            if key not in seen_keys:
                seen_keys.add(key)
                structured.append({**q, 'type': 'opening', 'competency': 'Opening', 'ddg': False})
            if len(structured) >= count:
                break

    if 'culture_fit' in active_types and len(structured) < count:
        pool = [q for q in CULTURE_FIT_QUESTIONS if experience_level in q.get('levels', [experience_level])]
        rng.shuffle(pool)
        for q in pool:
            key = q['text'].lower()[:60]
            if key not in seen_keys:
                seen_keys.add(key)
                structured.append({**q, 'type': 'culture_fit', 'competency': 'Culture Fit', 'ddg': False})
            if len(structured) >= count:
                break

    # ── Finalise ──────────────────────────────────────────────────
    result = structured[:count]
    for i, q in enumerate(result):
        q['id'] = i + 1
        q['level'] = experience_level
        q.setdefault('follow_ups', [])
        q.setdefault('tips', '')
    return result


def _web_search_context(job_title, experience_level='mid'):
    """Fetch brief context from DuckDuckGo instant-answer API to enrich the AI prompt."""
    try:
        query = f'{job_title} interview questions key skills responsibilities'
        url = 'https://api.duckduckgo.com/?' + urllib.parse.urlencode({
            'q': query, 'format': 'json', 'no_html': '1', 'skip_disambig': '1',
        })
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 HRBot/1.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        snippets = []
        if data.get('AbstractText'):
            snippets.append(data['AbstractText'][:400])
        for topic in (data.get('RelatedTopics') or [])[:3]:
            if isinstance(topic, dict) and topic.get('Text'):
                snippets.append(topic['Text'][:200])
        if snippets:
            return '\n\nWeb research about this role:\n' + '\n'.join(f'• {s}' for s in snippets)
    except Exception as exc:
        _logger.debug('DDG web search failed (non-critical): %s', exc)
    return ''


def _call_claude_api(prompt, api_key, model='claude-haiku-4-5-20251001'):
    """POST to Anthropic Messages API and return the text response."""
    payload = json.dumps({
        'model': model,
        'max_tokens': 8192,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode('utf-8'))
    return result['content'][0]['text']


def _generate_questions_ai(job_title, experience_level, competencies, question_types, count,
                            company_context, industry, api_key):
    """Generate role-specific interview questions using Claude with optional web search context."""

    search_ctx = _web_search_context(job_title, experience_level)

    level_labels = {
        'junior':    'Junior (0–2 years experience)',
        'mid':       'Mid-Level (3–5 years experience)',
        'senior':    'Senior (6–10 years experience)',
        'executive': 'Executive (10+ years experience)',
    }
    level_label = level_labels.get(experience_level, experience_level)

    type_map = {
        'behavioral':  'Behavioral (STAR method)',
        'technical':   'Technical / Role-Specific',
        'situational': 'Situational (scenario-based)',
        'opening':     'Opening (background & motivation)',
        'culture_fit': 'Culture Fit',
    }
    active_types = question_types or list(type_map.keys())
    types_desc = ', '.join(type_map.get(t, t) for t in active_types)

    industry_text  = f' in the {industry} industry' if industry else ''
    context_text   = f'\n\nRole/company context provided by recruiter: {company_context}' if company_context else ''
    comp_text      = (
        f'\n\nFocus behavioral questions specifically on these competencies: {", ".join(competencies)}'
        if competencies else ''
    )

    prompt = f"""You are a senior HR consultant and expert technical interviewer with deep knowledge of hiring across all industries and specialised roles.

Generate exactly {count} interview questions for a {level_label} {job_title} position{industry_text}.{context_text}{comp_text}{search_ctx}

CRITICAL RULES — follow every one:
1. Questions MUST be HIGHLY SPECIFIC to "{job_title}". Reference the actual tools, platforms, technologies, workflows, domain knowledge, standards, and day-to-day scenarios someone in this exact role encounters.
2. NEVER write generic questions that could apply to any job (e.g. "Tell me about a time you solved a problem" is too vague — make it specific to {job_title}).
3. For technical questions: name the specific technologies, APIs, frameworks, platforms or skills relevant to {job_title}.
4. Distribute the {count} questions proportionally across these types: {types_desc}.
5. Each question must have 2 realistic probing follow-ups and practical interviewer tips (what a strong answer looks like).

Return ONLY a valid JSON array — no markdown fences, no explanation text, no comments, just raw JSON starting with [ and ending with ]:
[
  {{
    "id": 1,
    "text": "Specific question text",
    "type": "technical",
    "competency": "Skill or competency being assessed",
    "follow_ups": ["Follow-up probe 1", "Follow-up probe 2"],
    "tips": "What a strong answer includes; red flags to watch for",
    "level": "{experience_level}"
  }}
]

Valid type values: technical, behavioral, situational, opening, culture_fit
Generate exactly {count} questions numbered 1 through {count}."""

    raw = _call_claude_api(prompt, api_key).strip()

    # Strip markdown code fences if Claude wrapped the JSON
    if raw.startswith('```'):
        lines = raw.split('\n')
        end = len(lines) - 1 if lines[-1].strip() == '```' else len(lines)
        raw = '\n'.join(lines[1:end]).strip()

    questions = json.loads(raw)

    result = []
    for i, q in enumerate(questions[:count]):
        result.append({
            'id': i + 1,
            'text': q.get('text', ''),
            'type': q.get('type', 'technical'),
            'competency': q.get('competency') or q.get('type', 'General').replace('_', ' ').title(),
            'follow_ups': q.get('follow_ups') or [],
            'tips': q.get('tips', ''),
            'level': experience_level,
            'ai_generated': True,
        })
    return result


# ───────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────

def _json_body():
    try:
        data = request.httprequest.data
        if data:
            return json.loads(data.decode('utf-8'))
    except Exception:
        pass
    return {}


def _ok(**kwargs):
    d = {'ok': True}
    d.update(kwargs)
    return request.make_response(
        json.dumps(d),
        headers=[('Content-Type', 'application/json')]
    )


def _err(msg, status=400):
    return request.make_response(
        json.dumps({'ok': False, 'error': msg}),
        headers=[('Content-Type', 'application/json')],
        status=status
    )


# ───────────────────────────────────────────────────────────────
# CONTROLLER
# ───────────────────────────────────────────────────────────────

class HrsdInterviewController(http.Controller):

    @http.route('/hrsd/interview', type='http', auth='user', website=False, methods=['GET'])
    def interview_page(self, **kw):
        if not request.env.user._is_internal():
            return request.redirect('/web/login')
        require_hrsd_confidential_access()
        sessions = request.env['hr.interview.session'].sudo().search([], order='create_date desc', limit=20)
        sessions_data = [s.session_summary() for s in sessions]
        return request.render('hrsd.interview_page', {
            'sessions': sessions_data,
            'sessions_json': json.dumps(sessions_data),
            'csrf_token': request.csrf_token(),
            'brand': get_hrsd_branding(request.env),
        })

    @http.route('/hrsd/interview/generate', type='http', auth='user', methods=['POST'], csrf=False)
    def interview_generate(self, **kw):
        require_hrsd_confidential_access()
        body = _json_body()
        job_title = (body.get('job_title') or '').strip()
        if not job_title:
            return _err('Job title is required.')

        experience_level = body.get('experience_level') or 'mid'
        competencies = body.get('competencies') or []
        question_types = body.get('question_types') or ['behavioral', 'technical', 'situational', 'opening', 'culture_fit']
        count = max(5, min(30, int(body.get('count') or 12)))
        company_context = (body.get('company_context') or '').strip()
        industry = (body.get('industry') or '').strip()

        api_key = _get_claude_api_key()
        generation_method = 'static'

        try:
            if api_key:
                # Priority 1: Claude AI (best quality)
                questions = _generate_questions_ai(
                    job_title=job_title,
                    experience_level=experience_level,
                    competencies=competencies,
                    question_types=question_types,
                    count=count,
                    company_context=company_context,
                    industry=industry,
                    api_key=api_key,
                )
                generation_method = 'claude'
            else:
                # Priority 2: DuckDuckGo web search (free, role-specific)
                ddg_questions = _generate_questions_ddg(
                    job_title=job_title,
                    experience_level=experience_level,
                    competencies=competencies,
                    question_types=question_types,
                    count=count,
                    company_context=company_context,
                    industry=industry,
                )
                if ddg_questions:
                    questions = ddg_questions
                    generation_method = 'ddg'
                else:
                    # Priority 3: static question bank (fallback)
                    questions = _generate_questions(
                        job_title=job_title,
                        experience_level=experience_level,
                        competencies=competencies,
                        question_types=question_types,
                        count=count,
                        company_context=company_context,
                        industry=industry,
                    )
                    generation_method = 'static'

        except urllib.error.HTTPError as e:
            body_bytes = e.read()
            _logger.error("Claude API HTTP error %s: %s", e.code, body_bytes)
            msg = f'Claude API error {e.code}'
            try:
                err_data = json.loads(body_bytes)
                msg = err_data.get('error', {}).get('message', msg)
            except Exception:
                pass
            return _err(msg, 500)
        except Exception as e:
            _logger.exception("Question generation error")
            return _err(str(e), 500)

        detected_domain = _detect_role_domain(job_title)
        return _ok(
            questions=questions,
            domain=detected_domain,
            count=len(questions),
            ai_generated=(generation_method == 'claude'),
            generation_method=generation_method,
        )

    @http.route('/hrsd/interview/ai-status', type='http', auth='user', methods=['GET'])
    def interview_ai_status(self, **kw):
        require_hrsd_confidential_access()
        api_key = _get_claude_api_key()
        return request.make_response(
            json.dumps({'ok': True, 'ai_enabled': bool(api_key), 'has_key': bool(api_key)}),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/hrsd/interview/save-api-key', type='http', auth='user', methods=['POST'], csrf=False)
    def interview_save_api_key(self, **kw):
        require_hrsd_confidential_access()
        if not request.env.user._is_admin():
            return _err('Only administrators can update the API key.', 403)
        body = _json_body()
        key = (body.get('api_key') or '').strip()
        request.env['ir.config_parameter'].sudo().set_param('hrsd.claude_api_key', key)
        return _ok(saved=True, ai_enabled=bool(key))

    @http.route('/hrsd/interview/session/save', type='http', auth='user', methods=['POST'], csrf=False)
    def session_save(self, **kw):
        require_hrsd_confidential_access()
        body = _json_body()
        job_title = (body.get('job_title') or '').strip()
        if not job_title:
            return _err('Job title is required.')

        questions = body.get('questions') or []
        name = (body.get('name') or f"{job_title} — {datetime.now().strftime('%d %b %Y')}").strip()

        try:
            session = request.env['hr.interview.session'].sudo().create({
                'name': name,
                'job_title': job_title,
                'industry': (body.get('industry') or '').strip(),
                'experience_level': body.get('experience_level') or 'mid',
                'question_count': len(questions),
                'competencies': json.dumps(body.get('competencies') or []),
                'question_types': json.dumps(body.get('question_types') or []),
                'company_context': (body.get('company_context') or '').strip(),
                'questions_json': json.dumps(questions),
            })
        except Exception as e:
            _logger.exception("Session save error")
            return _err(str(e), 500)

        return _ok(id=session.id, name=session.name)

    @http.route('/hrsd/interview/history', type='http', auth='user', methods=['GET'])
    def interview_history(self, **kw):
        require_hrsd_confidential_access()
        sessions = request.env['hr.interview.session'].sudo().search([], order='create_date desc', limit=100)
        data = [s.session_summary() for s in sessions]
        return request.make_response(
            json.dumps({'ok': True, 'sessions': data}),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/hrsd/interview/session/<int:session_id>', type='http', auth='user', methods=['GET'])
    def session_detail(self, session_id, **kw):
        require_hrsd_confidential_access()
        session = request.env['hr.interview.session'].sudo().browse(session_id)
        if not session.exists():
            return _err('Session not found.', 404)
        data = session.session_summary()
        data['questions'] = session.get_questions()
        return request.make_response(
            json.dumps({'ok': True, 'session': data}),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/hrsd/interview/session/delete', type='http', auth='user', methods=['POST'], csrf=False)
    def session_delete(self, **kw):
        require_hrsd_confidential_access()
        body = _json_body()
        sid = int(body.get('id') or 0)
        rec = request.env['hr.interview.session'].sudo().browse(sid)
        if rec.exists():
            rec.unlink()
        return _ok()

    @http.route('/hrsd/interview/export/<int:session_id>', type='http', auth='user', methods=['GET'])
    def session_export(self, session_id, **kw):
        require_hrsd_confidential_access()
        session = request.env['hr.interview.session'].sudo().browse(session_id)
        if not session.exists():
            return request.not_found()

        questions = session.get_questions()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['#', 'Type', 'Competency', 'Question', 'Follow-up Questions', 'Interviewer Tips'])
        for q in questions:
            writer.writerow([
                q.get('id', ''),
                q.get('type', '').replace('_', ' ').title(),
                q.get('competency', ''),
                q.get('text', ''),
                ' | '.join(q.get('follow_ups', [])),
                q.get('tips', ''),
            ])

        filename = f"interview_questions_{session_id}.csv"
        return request.make_response(output.getvalue(), headers=[
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ])
