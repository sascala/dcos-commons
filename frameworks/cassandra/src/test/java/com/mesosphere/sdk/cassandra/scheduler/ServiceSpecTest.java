package com.mesosphere.sdk.cassandra.scheduler;

import com.mesosphere.sdk.specification.DefaultService;
import com.mesosphere.sdk.specification.DefaultServiceSpec;
import com.mesosphere.sdk.specification.yaml.YAMLServiceSpecFactory;
import org.junit.Assert;
import org.junit.BeforeClass;
import org.junit.ClassRule;
import org.junit.Test;
import org.junit.contrib.java.lang.system.EnvironmentVariables;

import java.io.File;
import java.net.URL;
import java.util.Collections;

import static com.mesosphere.sdk.specification.yaml.YAMLServiceSpecFactory.generateRawSpecFromYAML;

public class ServiceSpecTest {
    @ClassRule
    public static final EnvironmentVariables environmentVariables = new EnvironmentVariables();

    @BeforeClass
    public static void beforeAll() {
        environmentVariables.set("EXECUTOR_URI", "");
        environmentVariables.set("LIBMESOS_URI", "");
        environmentVariables.set("PORT0", "8080");

        environmentVariables.set("TASKCFG_ALL_SERVICE_NAME", "cassandra");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_CLUSTER_NAME", "cassandra");
        environmentVariables.set("NODES", "3");
        environmentVariables.set("FRAMEWORK_USER", "core");
        environmentVariables.set("CASSANDRA_CPUS", "0.1");
        environmentVariables.set("CASSANDRA_VERSION", "3.0.10");
        environmentVariables.set("CASSANDRA_MEMORY_MB", "512");
        environmentVariables.set("TASKCFG_ALL_JMX_PORT", "9000");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_STORAGE_PORT", "9001");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_SSL_STORAGE_PORT", "9002");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_NATIVE_TRANSPORT_PORT", "9003");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_RPC_PORT", "9004");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_HEAP_SIZE_MB", "4000");
        environmentVariables.set("TASKCFG_ALL_CASSANDRA_HEAP_NEW_MB", "400");
        environmentVariables.set("CASSANDRA_HEAP_GC", "CMS");
        environmentVariables.set("CASSANDRA_DISK_MB", "5000");
        environmentVariables.set("CASSANDRA_DISK_TYPE", "ROOT");
        URL resource = DefaultService.class.getClassLoader().getResource("cassandra_service.yml");
        environmentVariables.set("CONFIG_TEMPLATE_PATH", new File(resource.getPath()).getParent());

    }

    @Test
    public void test_yml_base() throws Exception {
        ServiceSpecDeserialization("cassandra_service.yml");
    }

    private void ServiceSpecDeserialization(String fileName) throws Exception {
        ClassLoader classLoader = getClass().getClassLoader();
        File file = new File(classLoader.getResource(fileName).getFile());
        DefaultServiceSpec serviceSpec = YAMLServiceSpecFactory
                .generateServiceSpec(generateRawSpecFromYAML(file));
        Assert.assertNotNull(serviceSpec);
        Assert.assertEquals(8080, serviceSpec.getApiPort());
        DefaultServiceSpec.getFactory(serviceSpec, Collections.emptyList());
    }

}
