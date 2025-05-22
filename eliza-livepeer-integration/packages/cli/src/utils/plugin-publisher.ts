import { promises as fs } from 'node:fs';
import path from 'node:path';
import { logger } from '@elizaos/core';
import { execa } from 'execa';
import semver from 'semver';
import {
  branchExists,
  createBranch,
  createPullRequest,
  forkExists,
  forkRepository,
  getFileContent,
  updateFile,
  ensureDirectory,
} from './github';
import { getGitHubToken, getRegistrySettings } from './registry';

interface PackageJson {
  name: string;
  version: string;
  description?: string;
  author?: string;
  repository?: {
    url?: string;
  };
  keywords?: string[];
  categories?: string[];
  platform?: 'node' | 'browser' | 'universal';
  type?: 'plugin' | 'project';
}

interface PluginMetadata {
  name: string;
  description: string;
  repository: {
    type: 'git' | 'npm';
    url: string;
  };
  maintainers: Array<{
    name: string;
    github: string;
  }>;
  categories: string[];
  tags: string[];
  versions: Array<{
    version: string;
    gitBranch?: string;
    gitTag?: string;
    npmVersion?: string;
    runtimeVersion: string;
    releaseDate: string;
    deprecated?: boolean;
  }>;
  latestStable: string | null;
  latestVersion: string;
  npm?: {
    name: string;
    url: string;
  };
  platform?: 'node' | 'browser' | 'universal';
  type: 'plugin' | 'project';
  installable?: boolean;
}

interface PublishTestResult {
  npmChecks: {
    loggedIn: boolean;
    canBuild: boolean;
    hasPermissions: boolean;
  };
  githubChecks: {
    hasToken: boolean;
    hasValidToken: boolean;
    hasForkAccess: boolean;
    canCreateBranch: boolean;
    canUpdateFiles: boolean;
    canCreatePR: boolean;
  };
  packageChecks: {
    hasPackageJson: boolean;
    hasValidName: boolean;
    hasVersion: boolean;
    hasRepository: boolean;
    versionNotExists: boolean;
  };
}

export async function testPublishToNpm(cwd: string): Promise<boolean> {
  try {
    // Check if logged in to npm
    await execa('npm', ['whoami']);
    logger.info('✓ Logged in to npm');

    // Test build
    logger.info('Testing build...');
    await execa('npm', ['run', 'build', '--dry-run'], { cwd });
    logger.info('✓ Build test successful');

    // Test publish access
    const pkgJson = JSON.parse(await fs.readFile(path.join(cwd, 'package.json'), 'utf-8'));
    await execa('npm', ['access', 'ls-packages'], { cwd });
    logger.info('✓ Have publish permissions');

    return true;
  } catch (error) {
    logger.error('Test failed:', error);
    if (error instanceof Error) {
      logger.error(`Error message: ${error.message}`);
      logger.error(`Error stack: ${error.stack}`);
    }
    return false;
  }
}

export async function testPublishToGitHub(
  cwd: string,
  packageJson: PackageJson,
  username: string
): Promise<boolean> {
  try {
    // Check GitHub token
    const token = await getGitHubToken();
    if (!token) {
      logger.error('GitHub token not found');
      return false;
    }
    logger.info('✓ GitHub token found');

    // Validate token permissions
    const response = await fetch('https://api.github.com/user', {
      headers: { Authorization: `token ${token}` },
    });
    if (!response.ok) {
      logger.error('Invalid GitHub token or insufficient permissions');
      return false;
    }
    logger.info('✓ GitHub token is valid');

    // Test registry access
    const settings = await getRegistrySettings();
    const [registryOwner, registryRepo] = settings.defaultRegistry.split('/');

    // Log the registry we're testing with
    logger.info(`Testing with registry: ${registryOwner}/${registryRepo}`);

    // Check fork permissions and create fork if needed
    const hasFork = await forkExists(token, registryOwner, registryRepo, username);
    logger.info(hasFork ? '✓ Fork exists' : '✓ Can create fork');

    if (!hasFork) {
      logger.info('Creating fork...');
      const forkCreated = await forkRepository(token, registryOwner, registryRepo);
      if (!forkCreated) {
        logger.error('Failed to create fork');
        return false;
      }
      logger.info('✓ Fork created');

      // Wait a moment for GitHub to complete the fork
      await new Promise((resolve) => setTimeout(resolve, 3000));
    }

    // Test branch creation
    const branchName = `test-${packageJson.name.replace(/^@elizaos\//, '')}-${packageJson.version}`;
    const hasBranch = await branchExists(token, username, registryRepo, branchName);
    logger.info(hasBranch ? '✓ Test branch exists' : '✓ Can create branch');

    if (!hasBranch) {
      logger.info('Creating branch...');
      const branchCreated = await createBranch(token, username, registryRepo, branchName, 'main');
      if (!branchCreated) {
        logger.error('Failed to create branch');
        return false;
      }
      logger.info('✓ Branch created');
    }

    // Test file update permissions - try a test file in the test directory
    const simpleName = packageJson.name.replace(/^@elizaos\//, '').replace(/[^a-zA-Z0-9-]/g, '-');
    // Change the path to try "test-files" directory rather than root
    const testPath = `test-files/${simpleName}-test.json`;
    logger.info(`Attempting to create test file: ${testPath} in branch: ${branchName}`);

    // Try to create the directory first if needed
    const dirCreated = await ensureDirectory(
      token,
      username,
      registryRepo,
      'test-files',
      branchName
    );
    if (!dirCreated) {
      logger.warn('Failed to create test directory, but continuing with file creation');
    }

    const canUpdate = await updateFile(
      token,
      username,
      registryRepo,
      testPath,
      JSON.stringify({ test: true, timestamp: new Date().toISOString() }),
      'Test file update',
      branchName // Use the test branch instead of main
    );
    if (!canUpdate) {
      logger.error('Cannot update files in repository');
      return false;
    }
    logger.info('✓ Can create and update files');

    return true;
  } catch (error) {
    logger.error('Test failed:', error);
    return false;
  }
}

export async function publishToNpm(cwd: string): Promise<boolean> {
  try {
    // Check if logged in to npm
    await execa('npm', ['whoami']);

    // Build the package
    logger.info('Building package...');
    await execa('npm', ['run', 'build'], { cwd, stdio: 'inherit' });

    // Publish to npm
    logger.info('Publishing to npm...');
    await execa('npm', ['publish'], { cwd, stdio: 'inherit' });

    return true;
  } catch (error) {
    logger.error('Failed to publish to npm:', error);
    return false;
  }
}

export async function publishToGitHub(
  cwd: string,
  packageJson: PackageJson,
  cliVersion: string,
  username: string,
  isTest = false
): Promise<boolean | { success: boolean; prUrl?: string }> {
  const token = await getGitHubToken();
  if (!token) {
    logger.error('GitHub token not found. Please set it using the login command.');
    return false;
  }

  if (isTest) {
    logger.info('Running in test mode - no actual changes will be made');
  }

  const settings = await getRegistrySettings();
  const [registryOwner, registryRepo] = settings.defaultRegistry.split('/');

  // Check for fork
  const hasFork = await forkExists(token, registryOwner, registryRepo, username);
  let forkFullName: string;

  if (!hasFork && !isTest) {
    logger.info(`Creating fork of ${settings.defaultRegistry}...`);
    const fork = await forkRepository(token, registryOwner, registryRepo);
    if (!fork) {
      logger.error('Failed to fork registry repository.');
      return false;
    }
    forkFullName = fork;
  } else {
    forkFullName = `${username}/${registryRepo}`;
    logger.info(`Using existing fork: ${forkFullName}`);
  }

  // Create version branch - use type in branch name
  const entityType = 'plugin';
  const branchName = `${entityType}-${packageJson.name.replace(/^@elizaos\//, '')}-${packageJson.version}`;
  const hasBranch = await branchExists(token, username, registryRepo, branchName);

  if (!hasBranch && !isTest) {
    logger.info(`Creating branch ${branchName}...`);
    const created = await createBranch(token, username, registryRepo, branchName);
    if (!created) {
      logger.error('Failed to create branch.');
      return false;
    }
  }

  // Update package metadata
  const packageName = packageJson.name.replace(/^@elizaos\//, '');
  const packagePath = `packages/${packageName}.json`;
  const existingContent = await getFileContent(token, registryOwner, registryRepo, packagePath);

  let metadata: PluginMetadata;
  const currentDate = new Date().toISOString();
  const repositoryUrl = packageJson.repository?.url || `github:${username}/${packageName}`;

  if (existingContent) {
    try {
      metadata = JSON.parse(existingContent);

      if (metadata.versions.some((v) => v.version === packageJson.version)) {
        logger.error(`Version ${packageJson.version} already exists in registry.`);
        return false;
      }

      // Add new version information
      metadata.versions.push({
        version: packageJson.version,
        gitBranch: packageJson.version,
        gitTag: `v${packageJson.version}`,
        runtimeVersion: cliVersion,
        releaseDate: currentDate,
        deprecated: false,
      });

      metadata.latestVersion = packageJson.version;

      // Update latestStable if this is a stable release
      if (
        !semver.prerelease(packageJson.version) &&
        (!metadata.latestStable || semver.gt(packageJson.version, metadata.latestStable))
      ) {
        metadata.latestStable = packageJson.version;
      }

      // Update type if specified
      if (packageJson.type) {
        metadata.type = packageJson.type;
        // Projects are not installable in agents
        metadata.installable = packageJson.type === 'plugin';
      }

      // Add plugin tag if it's a plugin and doesn't already have it
      if (
        metadata.type === 'plugin' &&
        Array.isArray(metadata.tags) &&
        !metadata.tags.includes('plugin')
      ) {
        metadata.tags.push('plugin');
      }

      // Update platform if specified
      if (packageJson.platform) {
        metadata.platform = packageJson.platform;
      }

      // Update tags and categories if changed
      if (packageJson.keywords?.length) {
        metadata.tags = packageJson.keywords;
      }

      if (packageJson.categories?.length) {
        metadata.categories = packageJson.categories;
      }
    } catch (error) {
      logger.error(`Error parsing existing metadata: ${error.message}`);
      logger.info('Creating new metadata');
      metadata = null;
    }
  }

  if (!metadata) {
    // Create new metadata in V2 format
    metadata = {
      name: packageJson.name,
      description: packageJson.description || '',
      repository: {
        type: repositoryUrl.startsWith('npm:') ? 'npm' : 'git',
        url: repositoryUrl,
      },
      maintainers: [
        {
          name: username,
          github: username,
        },
      ],
      categories: packageJson.categories || [],
      tags: packageJson.keywords || [],
      versions: [
        {
          version: packageJson.version,
          gitBranch: packageJson.version,
          gitTag: `v${packageJson.version}`,
          runtimeVersion: cliVersion,
          releaseDate: currentDate,
          deprecated: false,
        },
      ],
      latestStable: semver.prerelease(packageJson.version) ? null : packageJson.version,
      latestVersion: packageJson.version,
      type: entityType,
      installable: entityType === 'plugin', // Only plugins are installable
    };

    // Add "plugin" tag if it's a plugin and doesn't already have it
    if (entityType === 'plugin' && !metadata.tags.includes('plugin')) {
      metadata.tags.push('plugin');
    }

    // Add platform if specified
    if (packageJson.platform) {
      metadata.platform = packageJson.platform;
    }
  }

  if (!isTest) {
    // Update package file
    const updated = await updateFile(
      token,
      username,
      registryRepo,
      packagePath,
      JSON.stringify(metadata, null, 2),
      `Update ${packageJson.name} to version ${packageJson.version}`,
      branchName
    );

    if (!updated) {
      logger.error('Failed to update package metadata.');
      return false;
    }

    // Update index.json for V2 registry
    try {
      const indexContent = await getFileContent(token, username, registryRepo, 'index.json');
      if (indexContent) {
        const index = JSON.parse(indexContent);
        const isNew = !index.__v2?.packages?.[packageJson.name];

        // Ensure v2 structure exists
        if (!index.__v2) {
          index.__v2 = {
            version: '2.0.0',
            packages: {},
            categories: {},
            types: {
              plugin: [],
              project: [],
            },
          };
        }

        // Ensure types collection exists
        if (!index.__v2.types) {
          index.__v2.types = {
            plugin: [],
            project: [],
          };
        }

        // Update package entry
        index.__v2.packages[packageJson.name] = packagePath;

        // Add only the current plugin to the plugin types array
        if (!index.__v2.types.plugin) {
          index.__v2.types.plugin = [];
        }
        if (!index.__v2.types.plugin.includes(packageJson.name)) {
          index.__v2.types.plugin.push(packageJson.name);
        }

        // Update categories
        metadata.categories.forEach((category) => {
          if (!index.__v2.categories[category]) {
            index.__v2.categories[category] = [];
          }
          if (!index.__v2.categories[category].includes(packageJson.name)) {
            index.__v2.categories[category].push(packageJson.name);
          }
        });

        // Update index.json
        const indexUpdated = await updateFile(
          token,
          username,
          registryRepo,
          'index.json',
          JSON.stringify(index, null, 2),
          `${isNew ? 'Add' : 'Update'} ${packageJson.name} in registry index`,
          branchName
        );

        if (!indexUpdated) {
          logger.warn('Failed to update registry index.');
        }
      }
    } catch (error) {
      logger.warn(`Failed to update index.json: ${error.message}`);
    }

    // Create pull request
    const prUrl = await createPullRequest(
      token,
      registryOwner,
      registryRepo,
      `Add ${packageJson.name}@${packageJson.version} to registry`,
      `This PR adds ${packageJson.name} version ${packageJson.version} to the registry.

- Type: ${packageJson.type || 'plugin'}
- Installable: ${(packageJson.type || 'plugin') === 'plugin' ? 'Yes' : 'No - Project type'}
- Package name: ${packageJson.name}
- Version: ${packageJson.version}
- Runtime version: ${cliVersion}
- Description: ${packageJson.description || 'No description provided'}
- Repository: ${metadata.repository.url}
- Platform: ${metadata.platform || 'not specified'}
- Categories: ${metadata.categories.join(', ') || 'none'}
- Tags: ${metadata.tags.join(', ') || 'none'}

Submitted by: @${username}`,
      `${username}:${branchName}`,
      'main'
    );

    if (!prUrl) {
      logger.error('Failed to create pull request.');
      return false;
    }

    logger.success(`Pull request created: ${prUrl}`);

    // Return success with PR URL
    return {
      success: true,
      prUrl: prUrl,
    };
  } else {
    logger.info('Test successful - all checks passed');
    logger.info('Would create:');
    logger.info(`- Branch: ${branchName}`);
    logger.info(`- Package file: ${packagePath}`);
    logger.info(
      `- Type: ${packageJson.type || 'plugin'} (${(packageJson.type || 'plugin') === 'plugin' ? 'installable' : 'not installable'})`
    );
    logger.info(`- Pull request: Add ${packageJson.name}@${packageJson.version} to registry`);
  }

  return true;
}
