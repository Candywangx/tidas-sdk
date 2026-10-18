import type { ProcessSemanticIssueCode } from '../validation/process-semantics';
import { z } from 'zod';

/**
 * Validation mode types
 */
export type ValidationMode = 'strict' | 'weak' | 'ignore';

/**
 * Validation configuration interface
 */
export interface ValidationConfig {
  mode: ValidationMode;
  throwOnError?: boolean;
  includeWarnings?: boolean;
  deepValidation?: boolean; // Enable deep validation to report nested field errors even when parent structure is invalid
}

/**
 * Validation warning interface
 */
export interface ValidationWarning {
  path: string[];
  message: string;
  code: string;
  severity: 'low' | 'medium' | 'high';
}

export type ValidationIssueSeverity = 'error' | 'warning' | 'info';

export type ValidationIssueParamValue =
  | string
  | number
  | boolean
  | null
  | undefined;

export type ValidationIssueCode =
  | 'required_missing'
  | 'string_too_short'
  | 'string_too_long'
  | 'array_too_small'
  | 'array_too_large'
  | 'number_too_small'
  | 'number_too_large'
  | 'invalid_type'
  | 'invalid_format'
  | 'invalid_value'
  | 'unrecognized_keys'
  | 'invalid_union'
  | 'localized_text_language_not_in_tidas_enum'
  | 'localized_text_zh_must_include_chinese_character'
  | 'localized_text_en_must_not_contain_chinese_character'
  | 'cas_number_checksum_error'
  | 'custom'
  | 'unknown'
  | ProcessSemanticIssueCode;

export interface NormalizedValidationIssue {
  code: ValidationIssueCode;
  path: Array<string | number>;
  params?: Record<string, ValidationIssueParamValue>;
  severity: ValidationIssueSeverity;
  message?: string;
  rawCode?: string;
}

/**
 * Enhanced validation result type
 */
export type EnhancedValidationResult<T> =
  | {
      success: true;
      data: T;
      validationIssues: NormalizedValidationIssue[];
      warnings?: ValidationWarning[];
      mode: ValidationMode;
    }
  | {
      success: false;
      error: z.ZodError;
      validationIssues: NormalizedValidationIssue[];
      warnings?: ValidationWarning[];
      mode: ValidationMode;
    };

type ZodIssueLike = z.core.$ZodIssue & {
  exact?: boolean;
  expected?: string;
  format?: string;
  inclusive?: boolean;
  input?: unknown;
  keys?: string[];
  maximum?: number;
  minimum?: number;
  origin?: string;
  params?: Record<string, ValidationIssueParamValue>;
  values?: unknown[];
};

const LOCALIZED_TEXT_ZH_MUST_INCLUDE_CHINESE_CHARACTER_CODE =
  'localized_text_zh_must_include_chinese_character';
const LOCALIZED_TEXT_EN_MUST_NOT_CONTAIN_CHINESE_CHARACTER_CODE =
  'localized_text_en_must_not_contain_chinese_character';
const CAS_NUMBER_CHECKSUM_ERROR_CODE = 'cas_number_checksum_error';

const KNOWN_CUSTOM_VALIDATION_CODES = new Set<ValidationIssueCode>([
  LOCALIZED_TEXT_ZH_MUST_INCLUDE_CHINESE_CHARACTER_CODE,
  LOCALIZED_TEXT_EN_MUST_NOT_CONTAIN_CHINESE_CHARACTER_CODE,
  CAS_NUMBER_CHECKSUM_ERROR_CODE,
]);

/**
 * Error severity classification
 */
export enum ErrorSeverity {
  CRITICAL = 'critical',
  WARNING = 'warning',
  INFO = 'info',
}

/**
 * Critical error patterns that should always cause validation failure
 */
const CRITICAL_ERROR_PATTERNS = [
  'Required',
  'Expected string, received undefined',
  'Expected number, received undefined',
  'Expected object, received undefined',
  'Expected array, received undefined',
];

/**
 * Validation utilities class
 */
export class ValidationUtils {
  private static getPath(
    path: z.core.$ZodIssue['path']
  ): Array<string | number> {
    return path.map((segment) =>
      typeof segment === 'string' || typeof segment === 'number'
        ? segment
        : String(segment)
    );
  }

  private static getInputType(input: unknown): string {
    if (input === undefined) {
      return 'undefined';
    }

    if (input === null) {
      return 'null';
    }

    if (Array.isArray(input)) {
      return 'array';
    }

    return typeof input;
  }

  private static getValueAtPath(
    source: unknown,
    path: Array<string | number>
  ): unknown {
    return path.reduce<unknown>((currentValue, segment) => {
      if (currentValue === null || currentValue === undefined) {
        return undefined;
      }

      return (currentValue as Record<string | number, unknown>)[segment];
    }, source);
  }

  private static getTooBigCode(issue: ZodIssueLike): ValidationIssueCode {
    if (issue.origin === 'string') {
      return 'string_too_long';
    }

    if (issue.origin === 'array') {
      return 'array_too_large';
    }

    if (issue.origin === 'number' || issue.origin === 'bigint') {
      return 'number_too_large';
    }

    return 'unknown';
  }

  private static getTooSmallCode(issue: ZodIssueLike): ValidationIssueCode {
    if (issue.origin === 'string') {
      return 'string_too_short';
    }

    if (issue.origin === 'array') {
      return 'array_too_small';
    }

    if (issue.origin === 'number' || issue.origin === 'bigint') {
      return 'number_too_small';
    }

    return 'unknown';
  }

  private static getTooBigParams(
    issue: ZodIssueLike,
    actualInput?: unknown
  ): Record<string, ValidationIssueParamValue> | undefined {
    const inputValue = issue.input !== undefined ? issue.input : actualInput;
    const params: Record<string, ValidationIssueParamValue> = {
      exact: issue.exact,
      inclusive: issue.inclusive,
      maximum: issue.maximum,
      origin: issue.origin,
    };

    if (issue.origin === 'string' && typeof inputValue === 'string') {
      params.actualLength = Array.from(inputValue).length;
    } else if (issue.origin === 'array' && Array.isArray(inputValue)) {
      params.actualLength = inputValue.length;
    } else if (
      (issue.origin === 'number' || issue.origin === 'bigint') &&
      (typeof inputValue === 'number' || typeof inputValue === 'bigint')
    ) {
      params.actual = Number(inputValue);
    }

    return Object.values(params).some((value) => value !== undefined)
      ? params
      : undefined;
  }

  private static getTooSmallParams(
    issue: ZodIssueLike,
    actualInput?: unknown
  ): Record<string, ValidationIssueParamValue> | undefined {
    const inputValue = issue.input !== undefined ? issue.input : actualInput;
    const params: Record<string, ValidationIssueParamValue> = {
      exact: issue.exact,
      inclusive: issue.inclusive,
      minimum: issue.minimum,
      origin: issue.origin,
    };

    if (issue.origin === 'string' && typeof inputValue === 'string') {
      params.actualLength = Array.from(inputValue).length;
    } else if (issue.origin === 'array' && Array.isArray(inputValue)) {
      params.actualLength = inputValue.length;
    } else if (
      (issue.origin === 'number' || issue.origin === 'bigint') &&
      (typeof inputValue === 'number' || typeof inputValue === 'bigint')
    ) {
      params.actual = Number(inputValue);
    }

    return Object.values(params).some((value) => value !== undefined)
      ? params
      : undefined;
  }

  private static isXmlLangPath(issue: ZodIssueLike): boolean {
    return issue.path[issue.path.length - 1] === '@xml:lang';
  }

  private static getValidationIssueCode(
    issue: ZodIssueLike
  ): ValidationIssueCode {
    switch (issue.code) {
      case 'invalid_type':
        return issue.input === undefined ? 'required_missing' : 'invalid_type';
      case 'too_big':
        return this.getTooBigCode(issue);
      case 'too_small':
        return this.getTooSmallCode(issue);
      case 'invalid_format':
        return 'invalid_format';
      case 'invalid_value':
        return this.isXmlLangPath(issue)
          ? 'localized_text_language_not_in_tidas_enum'
          : 'invalid_value';
      case 'unrecognized_keys':
        return 'unrecognized_keys';
      case 'invalid_union':
        return 'invalid_union';
      case 'custom': {
        const validationCode =
          typeof issue.params?.validationCode === 'string'
            ? issue.params.validationCode
            : undefined;

        return validationCode &&
          KNOWN_CUSTOM_VALIDATION_CODES.has(
            validationCode as ValidationIssueCode
          )
          ? (validationCode as ValidationIssueCode)
          : 'custom';
      }
      default:
        return 'unknown';
    }
  }

  private static getValidationIssueParams(
    issue: ZodIssueLike,
    code: ValidationIssueCode,
    sourceData?: unknown
  ): Record<string, ValidationIssueParamValue> | undefined {
    const actualInput =
      issue.input !== undefined
        ? issue.input
        : this.getValueAtPath(sourceData, this.getPath(issue.path));

    switch (code) {
      case 'required_missing':
        return issue.expected
          ? {
              expected: issue.expected,
            }
          : undefined;
      case 'invalid_type':
        return {
          expected: issue.expected,
          received: this.getInputType(issue.input),
        };
      case 'string_too_long':
      case 'array_too_large':
      case 'number_too_large':
        return this.getTooBigParams(issue, actualInput);
      case 'string_too_short':
      case 'array_too_small':
      case 'number_too_small':
        return this.getTooSmallParams(issue, actualInput);
      case 'invalid_format':
        return issue.format
          ? {
              format: issue.format,
            }
          : undefined;
      case 'invalid_value':
      case 'localized_text_language_not_in_tidas_enum':
        return Array.isArray(issue.values)
          ? {
              allowedValues: issue.values.join(', '),
            }
          : undefined;
      case 'unrecognized_keys':
        return Array.isArray(issue.keys) && issue.keys.length > 0
          ? {
              keys: issue.keys.join(', '),
            }
          : undefined;
      default:
        return undefined;
    }
  }

  static normalizeIssue(
    issue: z.core.$ZodIssue,
    sourceData?: unknown,
    severity: ValidationIssueSeverity = 'error'
  ): NormalizedValidationIssue {
    const issueLike = issue as ZodIssueLike;
    const code = this.getValidationIssueCode(issueLike);
    const params = this.getValidationIssueParams(issueLike, code, sourceData);

    return {
      code,
      path: this.getPath(issue.path),
      params,
      severity,
      message: issue.message,
      rawCode: issue.code,
    };
  }

  static normalizeIssues(
    issues: z.core.$ZodIssue[],
    sourceData?: unknown,
    severity: ValidationIssueSeverity = 'error'
  ): NormalizedValidationIssue[] {
    return issues.map((issue) =>
      this.normalizeIssue(issue, sourceData, severity)
    );
  }

  /**
   * Categorize Zod error by severity
   */
  static categorizeError(error: z.core.$ZodIssue): ErrorSeverity {
    const message = error.message;

    // Check for critical patterns
    for (const pattern of CRITICAL_ERROR_PATTERNS) {
      if (message.includes(pattern)) {
        return ErrorSeverity.CRITICAL;
      }
    }

    // Type-specific categorization
    switch (error.code) {
      case 'invalid_type':
        // If input is undefined for required field, it's critical
        if (error.input === undefined) {
          return ErrorSeverity.CRITICAL;
        }
        return ErrorSeverity.WARNING;

      case 'too_small':
      case 'too_big':
        return ErrorSeverity.WARNING;

      case 'invalid_value':
        return ErrorSeverity.WARNING;

      case 'unrecognized_keys':
        return ErrorSeverity.INFO;

      default:
        return ErrorSeverity.WARNING;
    }
  }

  /**
   * Convert Zod issue to validation warning
   */
  static issueToWarning(issue: z.core.$ZodIssue): ValidationWarning {
    const severity = this.categorizeError(issue);

    return {
      path: issue.path.map((p) => String(p)),
      message: issue.message,
      code: issue.code,
      severity:
        severity === ErrorSeverity.CRITICAL
          ? 'high'
          : severity === ErrorSeverity.WARNING
            ? 'medium'
            : 'low',
    };
  }

  /**
   * Perform weak validation that returns warnings instead of errors
   */
  static performWeakValidation<T>(
    schema: z.ZodType<T>,
    data: any,
    config: ValidationConfig
  ): EnhancedValidationResult<T> {
    const result = schema.safeParse(data);

    if (result.success) {
      return {
        success: true,
        data: result.data,
        validationIssues: [],
        mode: config.mode,
      };
    }

    // Categorize errors
    const criticalErrors: z.core.$ZodIssue[] = [];
    const warnings: ValidationWarning[] = [];

    for (const issue of result.error.issues) {
      const severity = this.categorizeError(issue);

      if (severity === ErrorSeverity.CRITICAL) {
        criticalErrors.push(issue);
      } else {
        warnings.push(this.issueToWarning(issue));
      }
    }

    // If there are critical errors, validation fails
    if (criticalErrors.length > 0) {
      const criticalError = new z.ZodError(criticalErrors);
      return {
        success: false,
        error: criticalError,
        validationIssues: this.normalizeIssues(criticalErrors, data),
        warnings: config.includeWarnings ? warnings : undefined,
        mode: config.mode,
      };
    }

    // No critical errors - weak validation passes with warnings
    return {
      success: true,
      data: data as T, // Accept data as-is for weak validation
      validationIssues: [],
      warnings: config.includeWarnings ? warnings : undefined,
      mode: config.mode,
    };
  }

  /**
   * Recursively collect validation errors from nested objects
   * This validates nested objects independently, even when parent validation fails
   */
  private static collectNestedErrors(
    schema: z.ZodType<any>,
    data: any,
    path: string[] = [],
    maxDepth: number = 10
  ): z.core.$ZodIssue[] {
    const issues: z.core.$ZodIssue[] = [];

    // Prevent infinite recursion
    if (path.length >= maxDepth) {
      return issues;
    }

    // Try to get the schema definition (support both _def and def for different Zod versions)
    const schemaDef = (schema as any).def || (schema as any)._def;

    // Handle ZodObject schemas
    if (schemaDef?.type === 'object' || schemaDef?.typeName === 'ZodObject') {
      let shape;

      // Get shape (could be a function or object)
      if (typeof schemaDef.shape === 'function') {
        shape = schemaDef.shape();
      } else if (schemaDef.shape) {
        shape = schemaDef.shape;
      }

      if (shape) {
        // Debug: log the current path
        if (
          process.env.DEBUG_VALIDATION &&
          path.length > 0 &&
          path.length <= 4
        ) {
          console.log(`[Deep Validation] Checking path: ${path.join('.')}`);
          console.log(
            `  Fields at this level: ${Object.keys(shape).join(', ')}`
          );
        }

        // Validate each field independently
        for (const [key, fieldSchema] of Object.entries(shape)) {
          const fieldPath = [...path, key];
          const fieldData = data?.[key];

          // Always validate the field itself first
          const fieldResult = (fieldSchema as z.ZodType<any>).safeParse(
            fieldData
          );

          // Debug: log ALL field validations for name-related paths
          if (
            process.env.DEBUG_VALIDATION &&
            fieldPath.join('.').includes('name')
          ) {
            console.log(
              `[Deep Validation] Validating field: ${fieldPath.join('.')}`
            );
            console.log(
              `  Data exists: ${fieldData !== undefined}, Is object: ${typeof fieldData === 'object'}`
            );
            console.log(
              `  Validation result: ${fieldResult.success ? 'PASS' : 'FAIL'}`
            );
            if (!fieldResult.success) {
              console.log(`  Errors: ${fieldResult.error.issues.length}`);
              fieldResult.error.issues.forEach((issue) => {
                console.log(
                  `    - ${issue.path.join('.')}: ${issue.message} [${issue.code}]`
                );
              });
            }
          }

          if (!fieldResult.success) {
            // Add ALL errors with full path
            fieldResult.error.issues.forEach((issue) => {
              issues.push({
                ...issue,
                path: [...fieldPath, ...issue.path],
              });
            });
          }

          // Recursively check nested objects if data exists and is an object
          if (
            fieldData &&
            typeof fieldData === 'object' &&
            !Array.isArray(fieldData)
          ) {
            const nestedIssues = this.collectNestedErrors(
              fieldSchema as z.ZodType<any>,
              fieldData,
              fieldPath,
              maxDepth
            );
            issues.push(...nestedIssues);
          }
        }
      }
    }

    return issues;
  }

  /**
   * Perform deep validation on nested objects
   * This attempts to validate nested structures even when parent objects have errors
   */
  static performDeepValidation<T>(
    schema: z.ZodType<T>,
    data: any,
    config: ValidationConfig
  ): EnhancedValidationResult<T> {
    // First, perform standard validation
    const standardResult = schema.safeParse(data);

    if (standardResult.success) {
      return {
        success: true,
        data: standardResult.data,
        validationIssues: [],
        mode: config.mode,
      };
    }

    // Standard validation failed - now collect additional nested errors
    const allIssues = [...standardResult.error.issues];

    // Collect nested validation errors
    const nestedIssues = this.collectNestedErrors(schema, data);

    // Debug: log how many nested issues were found
    if (process.env.DEBUG_VALIDATION) {
      console.log(
        `[Deep Validation] Standard issues: ${allIssues.length}, Nested issues: ${nestedIssues.length}`
      );
      console.log('[Deep Validation] Standard error paths:');
      allIssues.forEach((issue) =>
        console.log(`  - ${issue.path.join('.')} [${issue.code}]`)
      );
      console.log('[Deep Validation] Nested error paths:');
      nestedIssues.forEach((issue) =>
        console.log(`  - ${issue.path.join('.')} [${issue.code}]`)
      );
    }

    // Merge nested issues, avoiding duplicates
    let addedCount = 0;
    nestedIssues.forEach((nestedIssue) => {
      const isDuplicate = allIssues.some(
        (existing) =>
          JSON.stringify(existing.path) === JSON.stringify(nestedIssue.path) &&
          existing.code === nestedIssue.code
      );

      if (!isDuplicate) {
        allIssues.push(nestedIssue);
        addedCount++;
      }
    });

    if (process.env.DEBUG_VALIDATION) {
      console.log(
        `[Deep Validation] Added ${addedCount} new issues, total: ${allIssues.length}`
      );
    }

    // Create a new ZodError with all collected issues
    const enhancedError = new z.ZodError(allIssues);

    return {
      success: false,
      error: enhancedError,
      validationIssues: this.normalizeIssues(allIssues, data),
      mode: config.mode,
    };
  }

  /**
   * Perform validation based on mode
   */
  static performValidation<T>(
    schema: z.ZodType<T>,
    data: any,
    config: ValidationConfig
  ): EnhancedValidationResult<T> {
    // If deep validation is enabled, use deep validation for strict mode
    if (config.deepValidation && config.mode === 'strict') {
      return this.performDeepValidation(schema, data, config);
    }

    switch (config.mode) {
      case 'strict': {
        const strictResult = schema.safeParse(data);
        if (strictResult.success) {
          return {
            success: true,
            data: strictResult.data,
            validationIssues: [],
            mode: config.mode,
          };
        } else {
          return {
            success: false,
            error: strictResult.error,
            validationIssues: this.normalizeIssues(
              strictResult.error.issues,
              data
            ),
            mode: config.mode,
          };
        }
      }

      case 'weak':
        return this.performWeakValidation(schema, data, config);

      case 'ignore':
        return {
          success: true,
          data: data as T,
          validationIssues: [],
          mode: config.mode,
        };

      default: {
        const unsupportedMode: string = config.mode;
        throw new Error(`Unknown validation mode: ${unsupportedMode}`);
      }
    }
  }
}

/**
 * Default validation configuration
 */
export const DEFAULT_VALIDATION_CONFIG: ValidationConfig = {
  mode: 'strict',
  throwOnError: false,
  includeWarnings: true,
  deepValidation: true, // Enable deep validation by default
};
