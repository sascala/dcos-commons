package org.apache.mesos.specification.yaml;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import org.apache.commons.io.FileUtils;
import org.apache.mesos.offer.TaskUtils;
import org.apache.mesos.specification.DefaultServiceSpec;
import org.apache.mesos.specification.ServiceSpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Generates {@link ServiceSpec} from a given YAML definition.
 */
public class YAMLServiceSpecFactory {
    private static final Logger LOGGER = LoggerFactory.getLogger(YAMLServiceSpecFactory.class);
    private static final ObjectMapper YAML_MAPPER = new ObjectMapper(new YAMLFactory());
    private static final Charset CHARSET = StandardCharsets.UTF_8;

    public static final RawServiceSpecification generateRawSpecFromYAML(File pathToYaml) throws Exception {
        return generateRawSpecFromYAML(FileUtils.readFileToString(pathToYaml, CHARSET));
    }

    public static final RawServiceSpecification generateRawSpecFromYAML(final String yaml) throws Exception {
        final String yamlWithEnv = TaskUtils.applyEnvToMustache(yaml, System.getenv());
        LOGGER.info("Rendered ServiceSpec: {}", yamlWithEnv);
        if (!TaskUtils.isMustacheFullyRendered(yamlWithEnv)) {
            throw new IllegalStateException("YAML contains unsubstituted variables.");
        }
        return YAML_MAPPER.readValue(yamlWithEnv.getBytes(CHARSET), RawServiceSpecification.class);
    }

    public static final DefaultServiceSpec generateServiceSpec(RawServiceSpecification rawServiceSpecification)
            throws Exception {
        return YAMLToInternalMappers.from(rawServiceSpecification);
    }

    public static final List<RawPlan> generateRawPlans(RawServiceSpecification rawServiceSpecification)
            throws Exception {
        List<RawPlan> rawPlans = new LinkedList<>();
        Set<Map.Entry<String, RawPlan>> rawPlanEntries = rawServiceSpecification.getPlans().entrySet();
        for (Map.Entry<String, RawPlan> rawPlanEntry : rawPlanEntries) {
            RawPlan rawPlan = rawPlanEntry.getValue();
            rawPlan.setName(rawPlanEntry.getKey());
            rawPlans.add(rawPlan);
        }

        return rawPlans;
    }
}
