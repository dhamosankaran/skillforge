export interface SkillResource {
  label: string
  url: string
}

/**
 * Curated learning resources for common skills.
 * Keys are lowercase, normalised skill names.
 */
export const SKILL_RESOURCES: Record<string, SkillResource> = {
  // Programming languages
  python: { label: 'Python Docs', url: 'https://docs.python.org/3/tutorial/' },
  javascript: { label: 'MDN JS Guide', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide' },
  typescript: { label: 'TypeScript Docs', url: 'https://www.typescriptlang.org/docs/' },
  java: { label: 'Java Tutorial', url: 'https://dev.java/learn/' },
  'c++': { label: 'CPP Reference', url: 'https://cppreference.com/' },
  go: { label: 'Go Tour', url: 'https://go.dev/tour/' },
  rust: { label: 'Rust Book', url: 'https://doc.rust-lang.org/book/' },
  kotlin: { label: 'Kotlin Docs', url: 'https://kotlinlang.org/docs/' },
  swift: { label: 'Swift Docs', url: 'https://docs.swift.org/swift-book/' },
  php: { label: 'PHP Manual', url: 'https://www.php.net/manual/en/' },
  ruby: { label: 'Ruby Docs', url: 'https://www.ruby-lang.org/en/documentation/' },
  scala: { label: 'Scala Docs', url: 'https://docs.scala-lang.org/' },
  r: { label: 'R Tutorial', url: 'https://www.w3schools.com/r/' },

  // Data & Databases
  sql: { label: 'SQLZoo', url: 'https://sqlzoo.net/' },
  mysql: { label: 'MySQL Docs', url: 'https://dev.mysql.com/doc/' },
  postgresql: { label: 'PostgreSQL Docs', url: 'https://www.postgresql.org/docs/' },
  mongodb: { label: 'MongoDB University', url: 'https://learn.mongodb.com/' },
  redis: { label: 'Redis Docs', url: 'https://redis.io/docs/' },
  elasticsearch: { label: 'Elastic Docs', url: 'https://www.elastic.co/guide/' },
  snowflake: { label: 'Snowflake Docs', url: 'https://docs.snowflake.com/' },
  bigquery: { label: 'BigQuery Docs', url: 'https://cloud.google.com/bigquery/docs' },

  // Data Science & ML
  pandas: { label: 'Pandas Docs', url: 'https://pandas.pydata.org/docs/' },
  numpy: { label: 'NumPy Docs', url: 'https://numpy.org/doc/' },
  'scikit-learn': { label: 'Scikit-learn Docs', url: 'https://scikit-learn.org/stable/' },
  tensorflow: { label: 'TensorFlow Tutorials', url: 'https://www.tensorflow.org/tutorials' },
  pytorch: { label: 'PyTorch Tutorials', url: 'https://pytorch.org/tutorials/' },
  'machine learning': { label: 'ML Crash Course', url: 'https://developers.google.com/machine-learning/crash-course' },
  'deep learning': { label: 'Fast.ai Course', url: 'https://course.fast.ai/' },
  nlp: { label: 'Hugging Face Course', url: 'https://huggingface.co/learn/nlp-course/' },
  tableau: { label: 'Tableau Training', url: 'https://www.tableau.com/learn/training' },
  'power bi': { label: 'Power BI Learning', url: 'https://learn.microsoft.com/en-us/power-bi/' },

  // Cloud & DevOps
  aws: { label: 'AWS Skill Builder', url: 'https://skillbuilder.aws/' },
  azure: { label: 'Microsoft Learn', url: 'https://learn.microsoft.com/en-us/azure/' },
  gcp: { label: 'Google Cloud Skills', url: 'https://cloudskillsboost.google/' },
  docker: { label: 'Docker Docs', url: 'https://docs.docker.com/get-started/' },
  kubernetes: { label: 'K8s Tutorials', url: 'https://kubernetes.io/docs/tutorials/' },
  terraform: { label: 'Terraform Docs', url: 'https://developer.hashicorp.com/terraform/tutorials' },
  'ci/cd': { label: 'GitHub Actions Docs', url: 'https://docs.github.com/en/actions' },
  jenkins: { label: 'Jenkins Docs', url: 'https://www.jenkins.io/doc/' },
  ansible: { label: 'Ansible Docs', url: 'https://docs.ansible.com/' },
  linux: { label: 'Linux Journey', url: 'https://linuxjourney.com/' },

  // Web & Frameworks
  react: { label: 'React Docs', url: 'https://react.dev/learn' },
  vue: { label: 'Vue Docs', url: 'https://vuejs.org/guide/' },
  angular: { label: 'Angular Docs', url: 'https://angular.dev/overview' },
  nodejs: { label: 'Node.js Docs', url: 'https://nodejs.org/en/learn' },
  django: { label: 'Django Docs', url: 'https://docs.djangoproject.com/' },
  fastapi: { label: 'FastAPI Docs', url: 'https://fastapi.tiangolo.com/tutorial/' },
  flask: { label: 'Flask Docs', url: 'https://flask.palletsprojects.com/' },
  graphql: { label: 'GraphQL Learn', url: 'https://graphql.org/learn/' },
  'rest api': { label: 'REST API Tutorial', url: 'https://restfulapi.net/' },
  'restful apis': { label: 'REST API Tutorial', url: 'https://restfulapi.net/' },

  // Data Engineering
  spark: { label: 'Spark Docs', url: 'https://spark.apache.org/docs/latest/' },
  kafka: { label: 'Kafka Quickstart', url: 'https://kafka.apache.org/quickstart' },
  airflow: { label: 'Airflow Docs', url: 'https://airflow.apache.org/docs/' },
  dbt: { label: 'dbt Learn', url: 'https://courses.getdbt.com/' },
  'data pipelines': { label: 'dbt Learn', url: 'https://courses.getdbt.com/' },
  etl: { label: 'Data Engineering Course', url: 'https://www.coursera.org/specializations/data-engineering' },

  // Testing
  jest: { label: 'Jest Docs', url: 'https://jestjs.io/docs/getting-started' },
  pytest: { label: 'pytest Docs', url: 'https://docs.pytest.org/' },
  selenium: { label: 'Selenium Docs', url: 'https://www.selenium.dev/documentation/' },
  'a/b testing': { label: 'A/B Testing Guide', url: 'https://www.optimizely.com/optimization-glossary/ab-testing/' },

  // Soft skills & methodologies
  agile: { label: 'Agile Guide', url: 'https://www.atlassian.com/agile' },
  scrum: { label: 'Scrum Guide', url: 'https://scrumguides.org/' },
  'system design': { label: 'System Design Primer', url: 'https://github.com/donnemartin/system-design-primer' },
  'communication': { label: 'Coursera Communication', url: 'https://www.coursera.org/courses?query=communication+skills' },
  leadership: { label: 'Leadership Courses', url: 'https://www.coursera.org/courses?query=leadership' },
  'project management': { label: 'PMI Resources', url: 'https://www.pmi.org/learning/library' },
}

/**
 * Look up a resource for a skill name (case-insensitive, normalised).
 * Returns undefined if no resource is mapped.
 */
export function getSkillResource(skill: string): SkillResource | undefined {
  const key = skill.toLowerCase().trim()
  return SKILL_RESOURCES[key]
}
